# reflex-webcam

Package for a webcam for the [Reflex Framework](https://github.com/reflex-dev/reflex)


## ⚙️ Installation

Open a terminal and run (Requires Python 3.10+):

```bash
pip install reflex-webcam
```

## Import package

```python
import reflex_webcam as webcam
```

## Simple Usage (Screenshot)

This example below allows a user to use the webcam and take a screenshot, which is rendered under the webcam live feed.

To run the app shown below just copy and paste the code in a Reflex app. 

```python
import time
from pathlib import Path
from urllib.request import urlopen
from PIL import Image

import reflex as rx
import reflex_webcam as webcam


# Identifies a particular webcam component in the DOM
WEBCAM_REF = "webcam"


class State(rx.State):
    last_screenshot: Image.Image | None = None
    last_screenshot_timestamp: str = ""
    loading: bool = False

    def handle_screenshot(self, img_data_uri: str):
        """Webcam screenshot upload handler.
        Args:
            img_data_uri: The data uri of the screenshot (from upload_screenshot).
        """
        if self.loading:
            return
        self.last_screenshot_timestamp = time.strftime("%H:%M:%S")
        with urlopen(img_data_uri) as img:
            self.last_screenshot = Image.open(img)
            self.last_screenshot.load()
            # convert to webp during serialization for smaller size
            self.last_screenshot.format = "WEBP"  # type: ignore


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
        webcam.webcam(
            id=ref,
            on_click=webcam.upload_screenshot(
                ref=ref,
                handler=State.handle_screenshot,  # type: ignore
            ),
        ),
        last_screenshot_widget(),
        width="320px",
        align="center",
    )


def index() -> rx.Component:
    return rx.fragment(
        rx.center(
            webcam_upload_component(WEBCAM_REF),
            padding_top="3em",
        ),
    )


app = rx.App()
app.add_page(index)
```


# Advanced Usage (Video recording)

To run the webcam with video recording capabilities follow the instructions below to run the webcam_demo in this Github repo.

```bash
cd webcam_demo
reflex init
reflex run
```

You should see your app running at http://localhost:3000.

## Limitations

Currently the recording mechanism hardcodes `webm` as the video format, which is
not supported by Safari.