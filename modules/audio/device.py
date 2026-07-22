"""Audio hardware device discovery and selection manager.

Interfaces with macOS CoreAudio via sounddevice to enumerate microphones,
validate audio input specifications, and handle device selection.
"""

import sounddevice as sd
from core.exceptions import AudioDeviceError
from loguru import logger

from modules.audio.models import AudioDeviceInfo


class AudioDeviceManager:
    """Manages audio input device discovery, querying, and validation."""

    @staticmethod
    def list_input_devices() -> list[AudioDeviceInfo]:
        """Enumerate available audio input hardware devices.

        Returns:
            list[AudioDeviceInfo]: List of input-capable audio devices.

        Raises:
            AudioDeviceError: If hardware device querying encounters errors.
        """
        try:
            raw_devices = sd.query_devices()
            default_input_id = sd.default.device[0]
            devices: list[AudioDeviceInfo] = []

            for idx, dev in enumerate(raw_devices):
                max_inputs = int(dev.get("max_input_channels", 0))
                if max_inputs > 0:
                    info = AudioDeviceInfo(
                        device_id=idx,
                        name=str(dev.get("name", f"Device {idx}")),
                        max_input_channels=max_inputs,
                        default_sample_rate=float(
                            dev.get("default_samplerate", 44100.0)
                        ),
                        is_default=(idx == default_input_id),
                    )
                    devices.append(info)

            logger.debug(f"Discovered {len(devices)} audio input device(s).")
            return devices

        except Exception as exc:
            raise AudioDeviceError(
                message=f"Failed to query audio input devices: {exc}",
                details={"error": str(exc)},
            ) from exc

    @staticmethod
    def get_default_input_device() -> AudioDeviceInfo:
        """Retrieve default system audio input microphone device.

        Returns:
            AudioDeviceInfo: Default input device metadata.

        Raises:
            AudioDeviceError: If no valid default input device exists.
        """
        devices = AudioDeviceManager.list_input_devices()
        for dev in devices:
            if dev.is_default:
                return dev

        if devices:
            logger.warning("No default microphone flagged; using first available.")
            return devices[0]

        raise AudioDeviceError(
            message="No audio input devices detected on host system.",
            details={},
        )

    @staticmethod
    def get_device_by_id_or_name(
        device_spec: int | str | None = None,
    ) -> AudioDeviceInfo:
        """Retrieve and validate audio input device by ID index or substring name match.

        Args:
            device_spec: Device index, name substring, or None for default.

        Returns:
            AudioDeviceInfo: Validated input device info.

        Raises:
            AudioDeviceError: If device is not found or lacks input.
        """
        if device_spec is None:
            return AudioDeviceManager.get_default_input_device()

        devices = AudioDeviceManager.list_input_devices()

        if isinstance(device_spec, int):
            for dev in devices:
                if dev.device_id == device_spec:
                    return dev
            raise AudioDeviceError(
                message=f"Audio input device ID {device_spec} not found.",
                details={"requested_id": device_spec},
            )

        spec_lower = device_spec.lower()
        for dev in devices:
            if spec_lower in dev.name.lower():
                return dev

        raise AudioDeviceError(
            message=f"Audio input device matching name '{device_spec}' not found.",
            details={"requested_name": device_spec},
        )
