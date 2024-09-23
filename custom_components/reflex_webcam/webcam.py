"""Reflex custom component Webcam."""
from __future__ import annotations
from typing import Any, List

import reflex as rx
from reflex.vars import Var


class Webcam(rx.Component):
    """Wrapper for react-webcam component."""

    # The React library to wrap.
    library = "react-webcam"

    # The React component tag.
    tag = "Webcam"

    # If the tag is the default export from the module, you can set is_default = True.
    # This is normally used when components don't have curly braces around them when importing.
    is_default = True
    
    # The props of the React component.
    # Note: when Reflex compiles the component to Javascript,
    # `snake_case` property names are automatically formatted as `camelCase`.
    # The prop names may be defined in `camelCase` as well.

    # enable/disable audio
    audio: Var[bool] = False

    # format of screenshot
    screenshot_format: Var[str] = "image/jpeg"  # type: ignore

    # show camera preview and get the screenshot mirrored
    mirrored: Var[bool] = False

    # allow passing video constraints such as facingMode
    video_constraints: Var[dict] = {}

    special_props: set[Var] = [Var.create_safe("muted", _var_is_string=False)]

    def add_hooks(self) -> List[str]:
        if self.id is not None:
            return [
                f"refs['mediarecorder_{self.id}'] = useRef(null)",
            ]
        return []


webcam = Webcam.create


def upload_screenshot(ref: str, handler: rx.event.EventHandler):
    """Helper to capture and upload a screenshot from a webcam component.
    Args:
        ref: The ref of the webcam component.
        handler: The event handler that receives the screenshot.
    """
    return rx.call_script(
        f"refs['ref_{ref}'].current.getScreenshot()",
        callback=handler,
    )


def _validate_event_handler(handler: Any, name: str) -> None:
    if not isinstance(handler, rx.event.EventHandler):
        raise ValueError(
            f"{name} must be an EventHandler referenced from a state class, "
            f"got {handler}."
        )


def start_recording(
    ref: str,
    on_data_available: rx.event.EventHandler,
    on_start: rx.event.EventHandler | None = None,
    on_stop: rx.event.EventHandler | None = None,
    timeslice: str = "",
) -> str:
    """Helper to start recording a video from a webcam component.
    Args:
        ref: The ref of the webcam component.
        handler: The event handler that receives the video chunk by chunk.
        timeslice: How often to emit a chunk. Defaults to "" which means only at the end.
    Returns:
        The ref of the media recorder to stop recording.
    """
    _validate_event_handler(on_data_available, "on_data_available")
    on_data_available_event = rx.utils.format.format_event(
        rx.event.call_event_handler(on_data_available, arg_spec=lambda data: [data])
    )
    if on_start is not None:
        _validate_event_handler(on_start, "on_start")
        on_start_event = rx.utils.format.format_event(
            rx.event.call_event_handler(on_start, arg_spec=lambda e: [])
        )
        on_start_callback = f"mediaRecorderRef.current.addEventListener('start', () => applyEvent({on_start_event}, socket))"
    else:
        on_start_callback = ""

    if on_stop is not None:
        _validate_event_handler(on_stop, "on_stop")
        on_stop_event = rx.utils.format.format_event(
            rx.event.call_event_handler(on_stop, arg_spec=lambda e: [])
        )
        on_stop_callback = f"mediaRecorderRef.current.addEventListener('stop', () => applyEvent({on_stop_event}, socket))"
    else:
        on_stop_callback = ""

    return rx.call_script(
        f"""
        const handleDataAvailable = (e) => {{
            if (e.data.size > 0) {{
                var a = new FileReader();
                a.onload = (e) => {{
                    const _data = e.target.result
                    applyEvent({on_data_available_event}, socket)
                }}
                a.readAsDataURL(e.data);
            }}
        }}
        const mediaRecorderRef = refs['mediarecorder_{ref}']
        if (mediaRecorderRef.current != null) {{
            mediaRecorderRef.current.stop()
        }}
        mediaRecorderRef.current = new MediaRecorder(refs['ref_{ref}'].current.stream, {{mimeType: 'video/webm'}})
        mediaRecorderRef.current.addEventListener(
          "dataavailable",
          handleDataAvailable,
        );
        {on_start_callback}
        {on_stop_callback}
        mediaRecorderRef.current.start({timeslice})""",
    )


def stop_recording(ref: str):
    """Helper to stop recording a video from a webcam component.
    Args:
        ref: The ref of the webcam component.
        handler: The event handler that receives the video blob.
    """
    return rx.call_script(
        f"refs['mediarecorder_{ref}'].current.stop()",
    )