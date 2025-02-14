"""Take screenshots and video recordings from webcam."""

import time
from pathlib import Path
from urllib.request import urlopen

import reflex as rx
from PIL import Image
from reflex_webcam import strip_codec_part, upload_screenshot, webcam

# Identifies a particular webcam component in the DOM
WEBCAM_REF = "webcam"
VIDEO_FILE_NAME = "video.webm"

# The path containing the app
APP_PATH = Path(__file__)
APP_MODULE_DIR = APP_PATH.parent
SOURCE_CODE = [
    APP_MODULE_DIR.parent.parent / "custom_components/reflex_webcam/webcam.py",
    APP_PATH,
    APP_MODULE_DIR.parent / "requirements.txt",
]

# Mark Upload as used so StaticFiles can get mounted on /_upload
rx.upload()


SCREENSHOT_TAB = "screenshot_tab"
VIDEO_TAB = "video_tab"


class State(rx.State):
    last_screenshot: Image.Image | None = None
    last_screenshot_timestamp: str = ""
    loading: bool = False
    recording: bool = False
    n_recordings: int = 0  # incremented to cache bust the same video name
    active_tab: str = SCREENSHOT_TAB

    @rx.event
    def set_active_tab(self, tab_value: str):
        self.active_tab = tab_value

    @rx.event
    def handle_screenshot(self, img_data_uri: str):
        """Webcam screenshot upload handler.
        Args:
            img_data_uri: The data uri of the screenshot (from upload_screenshot).
        """
        if self.loading or not img_data_uri:
            return
        self.last_screenshot_timestamp = time.strftime("%H:%M:%S")
        with urlopen(img_data_uri) as img:
            self.last_screenshot = Image.open(img)
            self.last_screenshot.load()
            # convert to webp during serialization for smaller size
            self.last_screenshot.format = "WEBP"
        self.active_tab = SCREENSHOT_TAB

    def _video_path(self) -> Path:
        return Path(rx.get_upload_dir()) / self.video_path

    @rx.var(cache=True)
    def video_path(self) -> str:
        return f"{self.router.session.client_token}_{VIDEO_FILE_NAME}"

    @rx.var(cache=True, deps=["recording"])
    def video_exists(self) -> bool:
        return self._video_path().exists()

    @rx.event
    def on_start_recording(self):
        self.recording = True
        self.n_recordings += 1
        print("Started recording")  # noqa: T201
        with self._video_path().open("wb") as f:
            f.write(b"")

    @rx.event
    def handle_video_chunk(self, chunk: str):
        print("Got video chunk", len(chunk))  # noqa: T201
        with (
            self._video_path().open("ab") as f,
            urlopen(strip_codec_part(chunk)) as vid,
        ):
            f.write(vid.read())

    @rx.event
    def on_stop_recording(self):
        print(f"Stopped recording: {self._video_path()}")  # noqa: T201
        self.recording = False
        self.active_tab = VIDEO_TAB


def last_screenshot_widget() -> rx.Component:
    """Widget for displaying the last screenshot and timestamp."""
    return rx.box(
        rx.cond(
            State.last_screenshot,
            rx.fragment(
                rx.image(src=State.last_screenshot),
                rx.text(State.last_screenshot_timestamp),
            ),
            rx.center(
                rx.text("Click image to capture.", size="4"),
            ),
        ),
        height="270px",
    )


def webcam_upload_component(ref: str) -> rx.Component:
    """Component for displaying webcam preview and uploading screenshots.
    Args:
        ref: The ref of the webcam component.
    Returns:
        A reflex component.
    """
    return rx.vstack(
        webcam_obj := webcam(
            id=ref,
            audio=True,
            timeslice=1000,
            on_click=upload_screenshot(webcam_id=ref, handler=State.handle_screenshot),
            on_data_available=State.handle_video_chunk,
            on_start=State.on_start_recording,
            on_stop=State.on_stop_recording,
        ),
        rx.cond(
            ~State.recording,
            rx.button(
                "🟢 Start Recording",
                on_click=webcam_obj.start(),
                color_scheme="green",
                size="4",
            ),
            rx.button(
                "🟤 Stop Recording",
                on_click=webcam_obj.stop(),
                color_scheme="tomato",
                size="4",
            ),
        ),
        rx.tabs.root(
            rx.tabs.list(
                rx.cond(
                    State.last_screenshot,
                    rx.tabs.trigger("Screenshot", value=SCREENSHOT_TAB),
                ),
                rx.cond(
                    State.video_exists,
                    rx.tabs.trigger("Video", value=VIDEO_TAB),
                ),
            ),
            rx.tabs.content(
                last_screenshot_widget(),
                value=SCREENSHOT_TAB,
            ),
            rx.tabs.content(
                rx.video(
                    url=f"{rx.get_upload_url(State.video_path)}?r={State.n_recordings}",
                    playing=True,
                    width="320px",
                    key=State.recording,
                ),
                value=VIDEO_TAB,
            ),
            value=State.active_tab,
            on_change=State.set_active_tab,
            width="320px",
        ),
        width="320px",
        align="center",
    )


def index() -> rx.Component:
    return rx.fragment(
        rx.color_mode.button(position="top-right"),
        rx.center(
            webcam_upload_component(WEBCAM_REF),
            padding_top="3em",
        ),
        *[
            rx.vstack(
                rx.heading(f"Source Code: {p.name}"),
                rx.code_block(
                    p.read_text(),
                    language="python",
                    width="90%",
                    overflow_x="auto",
                ),
                margin_top="5em",
                padding_x="1em",
                width="100vw",
                align="center",
            )
            for p in SOURCE_CODE
        ],
    )


app = rx.App()
app.add_page(index)
