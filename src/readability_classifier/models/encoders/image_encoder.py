import concurrent.futures
import os
import re
from tempfile import TemporaryDirectory

import imgkit
from PIL import Image
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JavaLexer
from torch import Tensor

from readability_classifier.models.encoders.dataset_utils import (
    EncoderInterface,
    ReadabilityDataset,
)
from src.readability_classifier.utils.utils import open_image_as_tensor


class VisualEncoder(EncoderInterface):
    """
    A class for encoding code snippets as images.
    """

    def encode_dataset(self, unencoded_dataset: list[dict]) -> ReadabilityDataset:
        """
        Encodes the given dataset as images.
        :param unencoded_dataset: The unencoded dataset.
        :return: The encoded dataset.
        """
        encoded_dataset = []

        # Convert the list of dictionaries to a list of code snippet strings
        code_snippets = [sample["code_snippet"] for sample in unencoded_dataset]

        # Encode the code snippets
        encoded_code_snippets = dataset_to_image_tensors(code_snippets)

        # Convert the list of encoded code snippets to a ReadabilityDataset
        for i in range(len(encoded_code_snippets)):
            encoded_dataset.append(
                {
                    "image": encoded_code_snippets[i],
                }
            )

        return ReadabilityDataset(encoded_dataset)

    def encode_text(self, text: str) -> dict:
        """
        Encodes the given text as an image.
        :param text: The text to encode.
        :return: The encoded text as an image (in bytes).
        """
        return {"image": code_to_image_tensor(text)}


DEFAULT_OUT = "code.png"
DEFAULT_IN = "code.java"
DEFAULT_CSS = os.path.join(os.path.dirname(__file__), "../../../res/css/towards.css")
HEX_REGEX = r"#[0-9a-fA-F]{6}"


def _load_colors_from_css(file: str, hex_colors_regex: str = HEX_REGEX) -> set[str]:
    """
    Load the css file and return the colors in it using the regex
    :param file: path to the css file
    :param hex_colors_regex: regex to find the colors
    :return: list of colors
    """
    with open(file) as f:
        css_code = f.read()

    colors = re.findall(hex_colors_regex, css_code, re.MULTILINE)

    return set(colors)


def _convert_hex_to_rgba(hex_colors: set[str]) -> set[tuple[int, int, int, int]]:
    """
    Convert the hex colors to rgba
    :param hex_colors: set of hex colors
    :return: set of rgba colors
    """
    return {
        tuple(int(allowed_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
        for allowed_color in hex_colors
    }


def _remove_blur(
    img: Image, width: int, height: int, allowed_colors: set[tuple[int, int, int, int]]
) -> Image:
    """
    Remove the blur from the image.
    Set all the pixels that are not in the allowed colors to the closest allowed color.
    :param img: The image
    :param width: The width of the image
    :param height: The height of the image
    :param allowed_colors: The allowed colors
    :return: The image without blur
    """
    for i in range(width):
        for j in range(height):
            if img.getpixel((i, j)) not in allowed_colors:
                closest_color = min(
                    allowed_colors,
                    key=lambda x: sum(
                        abs(i - j) for i, j in zip(x, img.getpixel((i, j)), strict=True)
                    ),
                )
                img.putpixel((i, j), closest_color)

    return img


def _code_to_image(
    code: str,
    output: str = DEFAULT_OUT,
    css: str = DEFAULT_CSS,
    width: int = 128,
    height: int = 128,
):
    """
    Convert the given Java code to a visualisation/image.
    :param code: The code
    :param output: The path to save the image
    :param css: The css to use for styling the code
    :param width: The width of the image
    :param height: The height of the image
    :return: The image
    """
    # Convert the code to html
    lexer = JavaLexer()
    formatter = HtmlFormatter()
    html = highlight(code, lexer, formatter)

    # Set the options for imgkit
    options = {
        "format": "png",
        "quality": "100",
        "crop-h": str(height),
        "crop-w": str(width),
        "crop-x": "0",
        "crop-y": "0",
        "encoding": "UTF-8",
        "quiet": "",
        "disable-smart-width": "",
        "width": str(width),
        "height": str(height),
    }

    # Convert the html code to image
    imgkit.from_string(html, output, css=css, options=options)

    # Open the image
    img = Image.open(output)

    # Remove the blur from the image
    allowed_colors = _load_colors_from_css(css)
    allowed_colors = _convert_hex_to_rgba(allowed_colors)
    img = _remove_blur(img, width, height, allowed_colors)

    # Save the image
    img.save(output)


def code_to_image_tensor(
    text: str,
    out_dir: str = None,
    width: int = 128,
    height: int = 128,
    css: str = DEFAULT_CSS,
) -> Tensor:
    """
    Convert the given Java code to a visualisation/image and load it as a tensor.
    :param text: The code to visualize
    :param out_dir: The directory where the image should be stored. If None, a temporary
        directory is created.
    :param width: The width of the image
    :param height: The height of the image
    :param css: The css to use for styling the code
    :return: The image of the code as a tensor
    """
    temp_dir = None
    if out_dir is None:
        # Create a temporary directory
        temp_dir = TemporaryDirectory()
        out_dir = temp_dir.name
    else:
        # Create the save directory, if it does not exist
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)

    # Convert the code to an image
    image_file = os.path.join(out_dir, DEFAULT_OUT)
    _code_to_image(text, output=image_file, css=css, width=width, height=height)

    # Return the image as tensor 128x128x3 (RGB)
    image_as_tensor = open_image_as_tensor(image_file)

    # Delete the temporary directory
    if temp_dir is not None:
        temp_dir.cleanup()

    return image_as_tensor


def _process_code_to_image(
    snippet: str, idx: int, save_dir: str, css: str, width: int, height: int
) -> tuple[int, str]:
    """
    Process a single code snippet to an image. Used for parallel processing.
    :param snippet: The code snippet
    :param idx: The index of the code snippet
    :param save_dir: The directory where the image should be stored
    :param css: The css to use for styling the code
    :param width: The width of the image
    :param height: The height of the image
    """
    filename = os.path.join(save_dir, f"{idx}.png")
    _code_to_image(snippet, output=filename, css=css, width=width, height=height)
    return idx, filename


def dataset_to_image_tensors(
    snippets: list[str],
    save_dir: str = None,
    width: int = 128,
    height: int = 128,
    css: str = DEFAULT_CSS,
    parallel: bool = True,
) -> list[Tensor]:
    """
    Convert the given list with java code snippets to visualisations/images and load
    them as tensors.
    :param snippets: The list with java code snippets
    :param save_dir: The directory where the image should be stored.
    If None, a temporary directory is created.
    :param width: The width of the image
    :param height: The height of the image
    :param css: The css to use for styling the code
    :param parallel: Whether to use parallel processing
    :return: The images of the code snippets as tensors
    """
    temp_dir = None
    if save_dir is None:
        # Create a temporary directory
        temp_dir = TemporaryDirectory()
        save_dir = temp_dir.name
    else:
        # Create the save directory, if it does not exist
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)

    if parallel:
        # Create the visualisations
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    _process_code_to_image, snippet, idx, save_dir, css, width, height
                ): idx
                for idx, snippet in enumerate(snippets)
            }

            # TODO: Remove the following code?
            images = [None] * len(snippets)

            for future in concurrent.futures.as_completed(futures):
                idx, img_path = future.result()
                images[idx] = img_path
            # TODO: Remove the above code?
    else:
        # Create the visualisations
        for idx, snippet in enumerate(snippets):
            name = os.path.join(save_dir, f"{idx}.png")
            _code_to_image(snippet, output=name, css=css, width=width, height=height)

    # Read the images
    images_as_tensors = []
    for idx in range(len(snippets)):
        image_file = os.path.join(save_dir, f"{idx}.png")
        image_as_tensor = open_image_as_tensor(image_file)
        images_as_tensors.append(image_as_tensor)

    # Delete the temporary directory
    if temp_dir is not None:
        temp_dir.cleanup()

    return images_as_tensors
