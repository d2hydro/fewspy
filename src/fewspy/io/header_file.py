from pathlib import Path


def get_header_file(data_file: Path) -> Path:
    """Path to header-file based on data-file

    Args:
        data_file (Path): Path to data-file

    Returns:
        Path: Path to header-file
    """
    return data_file.with_name(f"{data_file.stem}_header{data_file.suffix}")
