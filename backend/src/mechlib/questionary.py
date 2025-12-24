from pathlib import Path

import questionary
from prompt_toolkit.shortcuts import CompleteStyle

@staticmethod
def input_path() -> Path:
    answer = questionary.path(
        "Where is your image path?",
        complete_style=CompleteStyle.MULTI_COLUMN
    ).ask()

    img_path = Path(answer).absolute()

    return img_path