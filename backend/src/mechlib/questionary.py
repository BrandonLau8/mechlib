from pathlib import Path

import questionary
from prompt_toolkit.shortcuts import CompleteStyle


def input_path() -> Path:
    answer = questionary.path(
        "Where is your image path?",
        complete_style=CompleteStyle.MULTI_COLUMN
    ).ask()

    img_path = Path(answer).absolute()

    return img_path


def from_terminal() -> dict:
        answers = questionary.form(
            description=questionary.text('Description: ', multiline=True),
            brand=questionary.text('Brand: '),

            materials=questionary.checkbox(
                'Materials: ',
                choices=[
                    'Plastic',
                    'Metal',
                    'Silicone'
                ],
            ),

            mechanism=questionary.text('Mechanism: '),
            project=questionary.text('Project: '),
            person=questionary.text('Person: ')

        ).ask()
        logging.info(answers)

        return answers