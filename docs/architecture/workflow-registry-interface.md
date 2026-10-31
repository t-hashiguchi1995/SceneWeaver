# Workflow Registry — interface only（Phase 1–2 実装なし）

将来、Comfy workflow を capability + I/O slots 付きで登録する。

現状の実質 Registry:

- `resolve_template_id_for_capability()`
- approved model ids
- `ComfyImageBackend._compile()`

Phase 1–2 では薄い `workflow_registry.py` スタブを追加しない（情報の三重化を避ける）。
