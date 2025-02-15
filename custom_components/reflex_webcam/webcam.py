"""Reflex custom component Webcam."""

from __future__ import annotations

from typing import Any, List, cast

import reflex as rx
from jinja2 import Environment
from reflex.event import EventType

START_RECORDING_JS_TEMPLATE = """
refs['mediarecorder_start_{{ ref }}'] = useCallback(() => {
    let mediaRecorderRef = refs['mediarecorder_{{ ref }}']
    if (mediaRecorderRef !== undefined) {
        mediaRecorderRef.stop()
    }
    try {
        mediaRecorderRef = new MediaRecorder(refs['{{ ref }}'].current.stream, {mimeType: 'video/webm'});
    } catch (e) {
        {{ on_error }}({message: e.message});
        return
    }
    refs['mediarecorder_{{ ref }}'] = mediaRecorderRef
    mediaRecorderRef.addEventListener(
        "dataavailable",
        (e) => {
            if (e.data.size > 0) {
                var a = new FileReader();
                a.onload = (e) => {
                    {{ on_data_available }}(e.target.result);
                }
                a.readAsDataURL(e.data);
            }
        }
    );
    {{ on_start_callback }}
    {{ on_stop_callback }}
    {{ on_error_callback }}
    addEventListener('beforeunload', () => {mediaRecorderRef.stop()})
    try {
        mediaRecorderRef.start({{ timeslice }})
    } catch (e) {
        {{ on_error }}({message: e.message});
    }
})
"""


def strip_codec_part(data_uri: str) -> str:
    parts = data_uri.split(";")
    for part in parts:
        if "codecs=" in part:
            parts.remove(part)
            break
    return ";".join(parts)


def _on_data_available_signature(data: rx.Var[str]) -> tuple[rx.Var[str]]:
    return (data,)


def _on_error_signature(error: rx.Var[dict]) -> tuple[rx.Var[dict]]:
    return (error,)


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
    audio: rx.Var[bool] = rx.Var.create(False)

    # format of screenshot
    screenshot_format: rx.Var[str] = rx.Var.create("image/jpeg")

    # show camera preview and get the screenshot mirrored
    mirrored: rx.Var[bool] = rx.Var.create(False)

    # allow passing video constraints such as facingMode
    video_constraints: rx.Var[dict] = rx.Var.create({})

    # When recording, how often to send interim data to the backend in milliseconds.
    timeslice: rx.Var[int]

    # These event handlers are used when recording.
    on_data_available: rx.EventHandler[_on_data_available_signature]
    on_start: rx.EventHandler[rx.event.no_args_event_spec]
    on_stop: rx.EventHandler[rx.event.no_args_event_spec]
    on_error: rx.EventHandler[_on_error_signature]

    special_props: list[rx.Var] = [rx.Var("muted")]

    @classmethod
    def create(cls, *children, **props) -> Webcam:
        props.setdefault("id", rx.vars.get_unique_variable_name())
        return cast(Webcam, super().create(*children, **props))

    def _exclude_props(self) -> List[str]:
        # These props are handled by hooks.
        return ["on_data_available", "on_start", "on_stop", "on_error", "timeslice"]

    def add_imports(self) -> rx.ImportDict:
        return {
            "react": [
                "useCallback",
                "useEffect",
            ]
        }

    def add_hooks(self) -> List[str | rx.Var]:
        on_data_available = self.event_triggers.get("on_data_available")
        if on_data_available is None:
            # No on_data_available, then no recording infrastructure is needed.
            return []
        if isinstance(on_data_available, rx.EventChain):
            on_data_available = rx.Var.create(on_data_available)

        on_start = self.event_triggers.get("on_start")
        if isinstance(on_start, rx.EventChain):
            on_start = rx.Var.create(on_start)
        if on_start is not None:
            on_start_callback = (
                f"mediaRecorderRef.addEventListener('start', {on_start!s})"
            )
        else:
            on_start_callback = ""

        on_stop = self.event_triggers.get("on_stop")
        if isinstance(on_stop, rx.EventChain):
            on_stop = rx.Var.create(on_stop)
        if on_stop is not None:
            on_stop_callback = "\n".join(
                [
                    f"mediaRecorderRef.addEventListener('stop', {on_stop!s})",
                    f"addEventListener('beforeunload', {on_stop!s})",
                ],
            )
        else:
            on_stop_callback = ""

        on_error = self.event_triggers.get("on_error")
        if isinstance(on_error, rx.EventChain):
            on_error = rx.Var.create(on_error)
        if on_error is None:
            on_error = "(_error) => console.log(_error)"
        on_error_callback = f"mediaRecorderRef.addEventListener('error', {on_error!s})"

        return [
            Environment()
            .from_string(START_RECORDING_JS_TEMPLATE)
            .render(
                ref=self.get_ref(),
                on_data_available=on_data_available,
                on_start_callback=on_start_callback,
                on_stop_callback=on_stop_callback,
                on_error_callback=on_error_callback,
                on_error=on_error,
                timeslice=str(rx.cond(self.timeslice, self.timeslice, "")).strip("{}"),
            )
        ]

    def start(self):
        if self.event_triggers.get("on_data_available") is None:
            raise ValueError("on_data_available is required to start recording.")
        return rx.call_script(f"refs['mediarecorder_start_{self.get_ref()}']()")

    def stop(self):
        return rx.call_script(
            f"""
            const mediaRecorderRef = refs['mediarecorder_{self.get_ref()}'];
            if (mediaRecorderRef) {{
                mediaRecorderRef.stop();
            }}
            """
        )

    def screenshot(self, handler: rx.EventHandler):
        """Helper to capture and upload a screenshot from a webcam component.
        Args:
            ref: The ref of the webcam component.
            handler: The event handler that receives the screenshot.
        """
        return upload_screenshot(self.id, handler)


webcam = Webcam.create


def upload_screenshot(webcam_id: str, handler: EventType[Any]):
    """Helper to capture and upload a screenshot from a webcam component.

    Args:
        webcam_id: The id of the webcam component.
        handler: The event handler that receives the screenshot.
    """
    return rx.call_script(
        f"refs['ref_{webcam_id}'].current.getScreenshot()",
        callback=handler,
    )
