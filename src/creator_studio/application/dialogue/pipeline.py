from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from creator_studio.domain.character import Character, Persona
from creator_studio.domain.ids import BeatId, CharacterId
from creator_studio.domain.story import (
    Beat,
    Scene,
    ScriptEvent,
    ScriptEventKind,
    ScriptEventStatus,
)
from creator_studio.infrastructure.prompts import PromptRegistry
from creator_studio.ports.llm import LLMGateway
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class DialogueCandidateDTO:
    id: str
    text: str
    tone: str
    critic_scores: dict[str, Any]


@dataclass
class GenerateDialogueResult:
    director_plan: dict[str, Any]
    voice_examples: list[dict[str, Any]]
    candidates: list[DialogueCandidateDTO]


class ContextAssembler:
    def assemble(
        self,
        *,
        character: Character,
        scene: Scene,
        beat: Beat,
        previous_beats: list[Beat],
        relationship: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "character": {
                "id": str(character.id),
                "name": character.display_name,
                "persona": {
                    "first_person": character.persona.first_person,
                    "second_person": character.persona.second_person,
                    "speech_rules": character.persona.speech_rules,
                    "forbidden_patterns": character.persona.forbidden_patterns,
                },
            },
            "relationship": relationship or {},
            "scene": {
                "id": str(scene.id),
                "title": scene.title,
                "objective": scene.objective,
            },
            "previous_beats": [
                {"seq": b.seq, "intent": b.intent, "subtext": b.subtext} for b in previous_beats
            ],
            "beat": {
                "id": str(beat.id),
                "intent": beat.intent,
                "subtext": beat.subtext,
                "emotion": {"name": beat.emotion.name, "intensity": beat.emotion.intensity},
                "action": beat.action,
            },
        }


class VoiceExampleRetriever:
    def retrieve(self, persona: Persona, *, limit: int = 3) -> list[dict[str, Any]]:
        examples = list(persona.voice_examples)
        # rule/tag filter: prefer examples tagged positive / matching emotion later
        positives = [e for e in examples if e.get("polarity", "positive") == "positive"]
        pool = positives or examples
        return pool[:limit]


class DialoguePipeline:
    def __init__(
        self,
        uow: UnitOfWork,
        llm: LLMGateway,
        prompts: PromptRegistry | None = None,
        *,
        on_script_change: Callable[[str], None] | None = None,
    ) -> None:
        self._uow = uow
        self._llm = llm
        self._prompts = prompts or PromptRegistry()
        self._context = ContextAssembler()
        self._voice = VoiceExampleRetriever()
        self._on_script_change = on_script_change

    def generate_candidates(
        self,
        *,
        beat_id: str,
        character_id: str,
        candidate_count: int = 3,
    ) -> GenerateDialogueResult:
        with self._uow as uow:
            beat = uow.beats.get(BeatId(beat_id))
            character = uow.characters.get(CharacterId(character_id))
            if beat is None or character is None:
                raise ValueError("beat or character not found")
            scene = uow.scenes.get(beat.scene_id)
            if scene is None:
                raise ValueError("scene not found")
            previous = [b for b in uow.beats.list_for_scene(beat.scene_id) if b.seq < beat.seq]

            # reject if locked speech already exists and caller tries regenerate without supersede
            locked = [
                e
                for e in uow.script_events.list_for_beat(beat.id)
                if e.locked and e.kind == ScriptEventKind.SPEECH
            ]
            if locked:
                raise PermissionError("locked ScriptEvent exists; unlock/supersede before regenerate")

            context = self._context.assemble(
                character=character,
                scene=scene,
                beat=beat,
                previous_beats=previous,
            )
            director_user = self._prompts.render(
                "dialogue/director_v1.jinja2",
                context_json=json.dumps(context, ensure_ascii=False, indent=2),
            )
            director_plan = self._llm.complete_json(
                system="Return JSON only.",
                user=director_user,
            )
            assert isinstance(director_plan, dict)

            voice_examples = self._voice.retrieve(character.persona)
            writer_user = self._prompts.render(
                "dialogue/writer_v1.jinja2",
                character_name=character.display_name,
                candidate_count=candidate_count,
                first_person=character.persona.first_person,
                second_person=character.persona.second_person,
                max_chars=character.persona.max_chars,
                max_fragments=character.persona.max_fragments,
                forbidden_patterns=character.persona.forbidden_patterns,
                director_json=json.dumps(director_plan, ensure_ascii=False),
                voice_examples_json=json.dumps(voice_examples, ensure_ascii=False),
                persona_json=json.dumps(
                    {
                        "first_person": character.persona.first_person,
                        "speech_rules": character.persona.speech_rules,
                    },
                    ensure_ascii=False,
                ),
            )
            lines = self._llm.complete_json(
                system="Return JSON array only.",
                user=writer_user,
                schema_hint="array",
            )
            if isinstance(lines, dict) and "candidates" in lines:
                lines = lines["candidates"]
            assert isinstance(lines, list)

            critic_user = self._prompts.render(
                "dialogue/critic_v1.jinja2",
                candidates_json=json.dumps(lines, ensure_ascii=False),
                director_json=json.dumps(director_plan, ensure_ascii=False),
                persona_json=json.dumps(
                    {"first_person": character.persona.first_person},
                    ensure_ascii=False,
                ),
            )
            critic = self._llm.complete_json(system="Return JSON only.", user=critic_user)
            assert isinstance(critic, dict)
            score_rows = critic.get("scores", [])

            # supersede previous candidates
            for old in uow.script_events.list_for_beat(beat.id):
                if old.status == ScriptEventStatus.CANDIDATE:
                    old.status = ScriptEventStatus.SUPERSEDED
                    uow.script_events.save(old)

            dtos: list[DialogueCandidateDTO] = []
            for idx, line in enumerate(lines[:candidate_count]):
                scores = score_rows[idx] if idx < len(score_rows) else {}
                event = ScriptEvent.create_candidate(
                    beat.id,
                    kind=ScriptEventKind.SPEECH,
                    speaker_id=character.id,
                    text=str(line.get("text", "")),
                    tone=str(line.get("tone", "")),
                    director_plan=director_plan,
                    critic_scores=scores,
                )
                uow.script_events.add(event)
                dtos.append(
                    DialogueCandidateDTO(
                        id=str(event.id),
                        text=event.text,
                        tone=event.tone,
                        critic_scores=scores,
                    )
                )
            uow.commit()
            return GenerateDialogueResult(
                director_plan=director_plan,
                voice_examples=voice_examples,
                candidates=dtos,
            )

    def lock_script_event(self, event_id: str, text: str | None = None) -> ScriptEvent:
        from creator_studio.domain.ids import ScriptEventId

        with self._uow as uow:
            event = uow.script_events.get(ScriptEventId(event_id))
            if event is None:
                raise ValueError("script event not found")
            # supersede sibling candidates
            for sibling in uow.script_events.list_for_beat(event.beat_id):
                if sibling.id != event.id and sibling.status == ScriptEventStatus.CANDIDATE:
                    sibling.status = ScriptEventStatus.SUPERSEDED
                    uow.script_events.save(sibling)
            event.lock(text)
            uow.script_events.save(event)
            uow.commit()
            beat_id = str(event.beat_id)
        if self._on_script_change is not None:
            self._on_script_change(beat_id)
        return event

    def update_locked_forbidden(self, event_id: str, new_text: str) -> None:
        """Demonstrate immutability: locked events reject in-place rewrite."""
        from creator_studio.domain.ids import ScriptEventId

        with self._uow as uow:
            event = uow.script_events.get(ScriptEventId(event_id))
            if event is None:
                raise ValueError("script event not found")
            event.assert_unlocked_for_rewrite()
            event.text = new_text
            uow.script_events.save(event)
            uow.commit()