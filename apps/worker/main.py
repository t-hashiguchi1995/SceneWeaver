from __future__ import annotations

import logging
import time

from sqlalchemy.exc import OperationalError

from creator_studio.domain.job import JobKind
from creator_studio.infrastructure.container import get_container, reset_container
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import clear_settings_cache, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sceneweaver.worker")


def run() -> None:
    settings = get_settings()
    logger.info("worker started id=%s", settings.worker_id)
    idle_polls = 0
    while True:
        try:
            # Refresh bindings periodically so E2E reset / settings changes apply.
            if idle_polls > 0 and idle_polls % 30 == 0:
                reset_engine()
                reset_container()
                clear_settings_cache()
            container = get_container()
            runner = container.claim_runner()
            claimed = runner.claim()
            if claimed is None:
                idle_polls += 1
                time.sleep(1.0)
                continue
            idle_polls = 0
            logger.info("claimed job=%s kind=%s", claimed.id, claimed.kind)
            if claimed.kind == JobKind.STUB.value:
                # Keep RUNNING long enough for SSE → UI to observe the transition.
                runner.heartbeat(claimed.id)
                delay = max(0.6, settings.fake_image_delay_ms / 1000.0)
                time.sleep(delay)
                done = runner.complete_stub(claimed.id)
                logger.info("completed job=%s status=%s", done.id, done.status)
            else:
                runner.fail(claimed.id, f"no handler for kind={claimed.kind}")
                logger.warning("unhandled kind=%s", claimed.kind)
        except OperationalError:
            logger.warning("sqlite operational error — resetting engine")
            reset_engine()
            reset_container()
            clear_settings_cache()
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            logger.exception("worker loop error: %s", exc)
            time.sleep(1.0)


if __name__ == "__main__":
    run()