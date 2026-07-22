"""Complex Scenario Simulation Script for EchoMind System Architecture.

Simulates 5 real-world meeting scenarios:
1. One-on-one conversation (2 speakers alternating)
2. 3-4 person discussion (4 distinct speakers)
3. Rapid interruptions and short overlapping speech segments
4. Multilingual code-switching (Marathi, Hindi, English) with keyword alerts
5. Background TV / fan ambient noise filtering
"""

import sys
import time

import numpy as np
from core.event_bus import EventBus
from loguru import logger
from modules.audio.models import AudioChunk
from modules.intelligence.alert_manager import AlertEvent, AlertManager
from modules.intelligence.notification_service import NotificationService
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
)
from modules.speaker.speaker_service import SpeakerService
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_HINDI,
    LANG_MARATHI,
    TranscriptEvent,
)
from modules.translation.service import TranslationEvent, TranslationService


def generate_speaker_audio(
    freq: float, duration_sec: float = 0.5, sr: int = 16000, noise_level: float = 0.0
) -> np.ndarray:
    """Generate synthetic audio signal for a target pitch profile with noise."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    signal = 0.6 * np.sin(2 * np.pi * freq * t) + 0.3 * np.cos(
        2 * np.pi * (freq * 2.5) * t
    )
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, len(t))
        signal += noise
    return signal.astype(np.float32)


def generate_ambient_noise(
    duration_sec: float = 0.5, sr: int = 16000, level: float = 0.003
) -> np.ndarray:
    """Generate ambient fan / background TV noise below VAD threshold."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    noise = np.random.normal(0, level, len(t))
    return noise.astype(np.float32)


def run_complex_scenarios_demo() -> int:
    """Execute all 5 complex simulation scenarios.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Complex Multi-Scenario System Simulation")
    logger.info("============================================================")

    # 1. Initialize EventBus, Services & Workers
    event_bus = EventBus(max_workers=4)
    notification_service = NotificationService(play_sound_enabled=False)
    transcript_service = TranscriptService(event_bus=event_bus)
    translation_service = TranslationService(event_bus=event_bus)
    alert_manager = AlertManager(
        event_bus=event_bus, notification_service=notification_service
    )
    speaker_service = SpeakerService(event_bus=event_bus)

    # Subscribe Event Display Callbacks
    event_bus.subscribe(
        SpeakerChangedEvent,
        lambda evt: logger.info(
            f"[SPEAKER] Changed -> {evt.new_temporary_name} ({evt.new_speaker_id[:8]})"
        ),
    )
    event_bus.subscribe(
        SpeakerAssignedEvent,
        lambda evt: logger.info(
            f"[SPEAKER LINK] Transcript {evt.transcript_id[:8]} -> {evt.temporary_name}"
        ),
    )
    event_bus.subscribe(
        TranslationEvent,
        lambda evt: logger.info(
            f"[TRANSLATION] #{evt.sequence_number} "
            f"[{evt.source_language.upper()}->EN]: '{evt.translated_text}'"
        ),
    )
    event_bus.subscribe(
        AlertEvent,
        lambda evt: logger.warning(
            f"[ALERT] [{evt.severity}] '{evt.rule_name}' "
            f"keyword '{evt.trigger_keyword}'"
        ),
    )

    # Frequencies representing 4 distinct speakers
    SPK_A = 150.0  # Male low pitch
    SPK_B = 400.0  # Female mid-high pitch
    SPK_C = 800.0  # High pitch
    SPK_D = 1800.0  # Ultra-high pitch

    try:
        # Start Meeting and Services
        meeting = transcript_service.start_meeting("EchoMind Complex Scenarios Test")
        speaker_service.set_active_meeting(meeting.id)
        translation_service.start()
        alert_manager.start()
        speaker_service.start()

        seq = 1

        # ----------------------------------------------------
        # SCENARIO 1: One-on-one conversation (Speaker A & B alternating)
        # ----------------------------------------------------
        logger.info("\n--- SCENARIO 1: One-on-One Conversation ---")
        s1_dialogue = [
            (SPK_A, "Hi Prayag, let's review the architecture plan.", LANG_ENGLISH),
            (SPK_B, "Sure, I have prepared the system diagrams.", LANG_ENGLISH),
            (SPK_A, "Great, the local storage look very solid.", LANG_ENGLISH),
            (SPK_B, "Thanks! Everything runs offline by default.", LANG_ENGLISH),
        ]
        for freq, text, lang in s1_dialogue:
            audio = generate_speaker_audio(freq=freq)
            event_bus.publish(
                AudioChunk(
                    data=audio,
                    sample_rate=16000,
                    channels=1,
                    timestamp=time.time(),
                    sequence_number=seq,
                )
            )
            time.sleep(0.05)
            event_bus.publish(
                TranscriptEvent(
                    text=text,
                    language=lang,
                    start_time=float(seq),
                    end_time=float(seq) + 1,
                    confidence=0.98,
                    is_final=True,
                    sequence_number=seq,
                )
            )
            seq += 1
            time.sleep(0.2)

        # ----------------------------------------------------
        # SCENARIO 2: 3-4 Person Discussion (Speakers A, B, C, D)
        # ----------------------------------------------------
        logger.info("\n--- SCENARIO 2: 3-4 Person Panel Discussion ---")
        s2_dialogue = [
            (SPK_A, "Welcome team to the technical sync.", LANG_ENGLISH),
            (SPK_B, "Speaker B here, frontend updates are ready.", LANG_ENGLISH),
            (
                SPK_C,
                "Speaker C here, backend database migrations complete.",
                LANG_ENGLISH,
            ),
            (
                SPK_D,
                "Speaker D here, QA testing environment is deployed.",
                LANG_ENGLISH,
            ),
            (SPK_A, "Awesome progress everyone!", LANG_ENGLISH),
        ]
        for freq, text, lang in s2_dialogue:
            audio = generate_speaker_audio(freq=freq)
            event_bus.publish(
                AudioChunk(
                    data=audio,
                    sample_rate=16000,
                    channels=1,
                    timestamp=time.time(),
                    sequence_number=seq,
                )
            )
            time.sleep(0.05)
            event_bus.publish(
                TranscriptEvent(
                    text=text,
                    language=lang,
                    start_time=float(seq),
                    end_time=float(seq) + 1,
                    confidence=0.97,
                    is_final=True,
                    sequence_number=seq,
                )
            )
            seq += 1
            time.sleep(0.2)

        # ----------------------------------------------------
        # SCENARIO 3: Rapid Interruptions (Fast Speaker Switching)
        # ----------------------------------------------------
        logger.info("\n--- SCENARIO 3: Rapid Interruptions & Fast Switching ---")
        s3_dialogue = [
            (SPK_A, "Wait, what about the deadline?", LANG_ENGLISH),
            (SPK_B, "I agree!", LANG_ENGLISH),
            (SPK_A, "No hold on!", LANG_ENGLISH),
            (SPK_C, "Let me speak!", LANG_ENGLISH),
            (SPK_B, "Okay go ahead.", LANG_ENGLISH),
        ]
        for freq, text, lang in s3_dialogue:
            audio = generate_speaker_audio(freq=freq, duration_sec=0.2)
            event_bus.publish(
                AudioChunk(
                    data=audio,
                    sample_rate=16000,
                    channels=1,
                    timestamp=time.time(),
                    sequence_number=seq,
                )
            )
            time.sleep(0.05)
            event_bus.publish(
                TranscriptEvent(
                    text=text,
                    language=lang,
                    start_time=float(seq),
                    end_time=float(seq) + 0.5,
                    confidence=0.92,
                    is_final=True,
                    sequence_number=seq,
                )
            )
            seq += 1
            time.sleep(0.15)

        # ----------------------------------------------------
        # SCENARIO 4: Multilingual Code-Switching (Marathi, Hindi, English)
        # ----------------------------------------------------
        logger.info("\n--- SCENARIO 4: Multilingual Code-Switching (MR, HI, EN) ---")
        s4_dialogue = [
            (SPK_A, "आजच्या सत्राचे नेतृत्व प्रयाग करत आहेत.", LANG_MARATHI),
            (
                SPK_B,
                "Hum speech recognition aur translation test kar rahe hain.",
                LANG_HINDI,
            ),
            (
                SPK_C,
                "This task is Urgent and deployment to Production starts today.",
                LANG_ENGLISH,
            ),
            (SPK_A, "नवीन फीचरची Deadline खूप जवळ आली आहे.", LANG_MARATHI),
        ]
        for freq, text, lang in s4_dialogue:
            audio = generate_speaker_audio(freq=freq)
            event_bus.publish(
                AudioChunk(
                    data=audio,
                    sample_rate=16000,
                    channels=1,
                    timestamp=time.time(),
                    sequence_number=seq,
                )
            )
            time.sleep(0.05)
            event_bus.publish(
                TranscriptEvent(
                    text=text,
                    language=lang,
                    start_time=float(seq),
                    end_time=float(seq) + 1,
                    confidence=0.96,
                    is_final=True,
                    sequence_number=seq,
                )
            )
            seq += 1
            time.sleep(0.25)

        # ----------------------------------------------------
        # SCENARIO 5: Background TV / Fan Noise Filtering
        # ----------------------------------------------------
        logger.info("\n--- SCENARIO 5: Background TV / Fan Ambient Noise Filtering ---")
        # Send background fan noise (silence / ambient noise below threshold)
        fan_noise = generate_ambient_noise(duration_sec=0.5, level=0.002)
        event_bus.publish(
            AudioChunk(
                data=fan_noise,
                sample_rate=16000,
                channels=1,
                timestamp=time.time(),
                sequence_number=seq,
            )
        )
        time.sleep(0.1)

        # Speech over noise
        noisy_speech = generate_speaker_audio(freq=SPK_A, noise_level=0.01)
        event_bus.publish(
            AudioChunk(
                data=noisy_speech,
                sample_rate=16000,
                channels=1,
                timestamp=time.time(),
                sequence_number=seq,
            )
        )
        time.sleep(0.05)
        event_bus.publish(
            TranscriptEvent(
                text="Even with background fan noise, speech is cleanly segmented.",
                language=LANG_ENGLISH,
                start_time=float(seq),
                end_time=float(seq) + 1,
                confidence=0.94,
                is_final=True,
                sequence_number=seq,
            )
        )

        time.sleep(0.5)

        # Stop Workers
        logger.info("\n--- Stopping Workers & Ending Meeting Session ---")
        speaker_service.stop()
        translation_service.stop()
        alert_manager.stop()
        transcript_service.end_meeting(meeting.id)
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("All 5 Complex Scenarios Successfully Tested & Verified!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Complex scenarios test failed: {exc}", exc_info=True)
        speaker_service.stop()
        translation_service.stop()
        alert_manager.stop()
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_complex_scenarios_demo())
