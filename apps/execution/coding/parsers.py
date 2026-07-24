"""MedDRA ASCII distribution file parser.

This module implements a production-oriented, streaming parser for MedDRA ASCII
distribution files that yields versioned five-level terminology and hierarchy
records in accordance with FDA 21 CFR Part 11 and GxP standards.
"""

import os
from typing import Any, Dict, Iterable, Iterator, List


class MedDRAParseError(ValueError):
    """Exception raised for errors in parsing MedDRA files.

    Attributes:
        message (str): Explanation of the error.
        file_name (str): Name of the source file.
        line_num (int): 1-based index of the line.
    """

    def __init__(self, message: str, file_name: str, line_num: int):
        self.message = message
        self.file_name = file_name
        self.line_num = line_num
        super().__init__(f"Parse error in '{file_name}' at line {line_num}: {message}")


class MedDRAParser:
    """Streaming parser for MedDRA ASCII distribution files.

    Yields versioned five-level terminology (LLT, PT, HLT, HLGT, SOC)
    and hierarchy records.
    """

    def __init__(self, dictionary_version: str, encoding: str = "utf-8"):
        """Initializes the MedDRAParser.

        Args:
            dictionary_version: The version tag of the MedDRA dictionary (e.g. "26.0").
            encoding: The file encoding to use when reading files (default "utf-8").

        Raises:
            ValueError: If dictionary_version is empty or None.
        """
        if not dictionary_version:
            raise ValueError("dictionary_version must be a non-empty string.")
        self.dictionary_version = dictionary_version
        self.encoding = encoding

    def detect_file_type(self, file_name: str) -> str:
        """Detects the MedDRA file type from a file name.

        Args:
            file_name: The file name (e.g. "llt.asc" or "MDHIER.ASC").

        Returns:
            str: One of "llt", "pt", "hlt", "hlgt", "soc", "mdhier".

        Raises:
            ValueError: If the file type cannot be auto-detected.
        """
        name = os.path.basename(file_name).lower()
        if "llt" in name:
            return "llt"
        elif "pt" in name:
            return "pt"
        elif "hlt" in name and "hlgt" not in name:
            return "hlt"
        elif "hlgt" in name:
            return "hlgt"
        elif "soc" in name:
            return "soc"
        elif "mdhier" in name:
            return "mdhier"
        else:
            raise ValueError(
                f"Cannot auto-detect MedDRA file type from file name: {file_name}"
            )

    def parse(
        self,
        file_input: Any,
        file_type: str = None,
        file_name: str = None,
    ) -> Iterator[Dict[str, Any]]:
        """Parses a MedDRA ASCII file streamingly and yields parsed records.

        Args:
            file_input: A file path, a file-like object, or an iterable of lines.
            file_type: One of "llt", "pt", "hlt", "hlgt", "soc", "mdhier". If None,
                it will try to auto-detect from file_name or file_input path.
            file_name: Optional file name for error context.

        Yields:
            Dict[str, Any]: A record dict with "type" and "data" keys.

        Raises:
            ValueError: If file_type is missing and cannot be auto-detected.
            MedDRAParseError: If a line fails to pass validation rules.
        """
        parsed_file_name = file_name or ""
        if isinstance(file_input, (str, bytes, os.PathLike)):
            if not parsed_file_name:
                parsed_file_name = os.path.basename(file_input)
            if not file_type:
                file_type = self.detect_file_type(parsed_file_name)

            with open(file_input, mode="r", encoding=self.encoding) as f:
                yield from self._parse_stream(f, file_type, parsed_file_name)
        else:
            if not parsed_file_name:
                parsed_file_name = "stream"
            if not file_type:
                file_type = self.detect_file_type(parsed_file_name)

            yield from self._parse_stream(file_input, file_type, parsed_file_name)

    def parse_in_batches(
        self,
        file_input: Any,
        file_type: str = None,
        file_name: str = None,
        batch_size: int = 1000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Parses the input file streamingly and yields records in batches.

        Args:
            file_input: A file path, a file-like object, or an iterable of lines.
            file_type: One of "llt", "pt", "hlt", "hlgt", "soc", "mdhier".
            file_name: Optional file name for error context.
            batch_size: The number of records per batch.

        Yields:
            List[Dict[str, Any]]: A list of parsed record dicts.

        Raises:
            ValueError: If batch_size is not a positive integer.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be a positive integer.")

        batch = []
        for record in self.parse(file_input, file_type, file_name):
            batch.append(record)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _parse_stream(
        self, stream: Iterable[str], file_type: str, file_name: str
    ) -> Iterator[Dict[str, Any]]:
        """Internal helper to parse lines from a stream."""
        file_type = file_type.lower()
        allowed_types = {"llt", "pt", "hlt", "hlgt", "soc", "mdhier"}
        if file_type not in allowed_types:
            raise ValueError(
                f"Invalid file_type: {file_type}. Must be one of {allowed_types}"
            )

        for idx, line in enumerate(stream, start=1):
            line_str = line.rstrip("\r\n")
            if not line_str:
                continue

            # Handle the standard trailing delimiter without creating a spurious empty field
            if line_str.endswith("$"):
                line_str = line_str[:-1]

            fields = [f.strip() for f in line_str.split("$")]

            if file_type == "llt":
                if len(fields) < 3:
                    raise MedDRAParseError(
                        f"Invalid LLT line: expected at least 3 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                llt_code, llt_name, pt_code = fields[0], fields[1], fields[2]

                if not llt_code:
                    raise MedDRAParseError(
                        "llt_code must not be empty.", file_name, idx
                    )
                if not llt_code.isdigit() or len(llt_code) != 8:
                    raise MedDRAParseError(
                        "llt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not llt_name:
                    raise MedDRAParseError(
                        "llt_name must not be empty.", file_name, idx
                    )
                if len(llt_name) > 255:
                    raise MedDRAParseError(
                        "llt_name exceeds maximum length of 255 characters.",
                        file_name,
                        idx,
                    )
                if not pt_code:
                    raise MedDRAParseError("pt_code must not be empty.", file_name, idx)
                if not pt_code.isdigit() or len(pt_code) != 8:
                    raise MedDRAParseError(
                        "pt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "term",
                    "data": {
                        "code": llt_code,
                        "term_name": llt_name,
                        "level": "LLT",
                        "dictionary_version": self.dictionary_version,
                    },
                }
                yield {
                    "type": "hierarchy",
                    "data": {
                        "llt_code": llt_code,
                        "pt_code": pt_code,
                        "hlt_code": "NONE",
                        "hlgt_code": "NONE",
                        "soc_code": "NONE",
                        "primary_soc_flag": None,
                        "dictionary_version": self.dictionary_version,
                    },
                }

            elif file_type == "pt":
                if len(fields) < 2:
                    raise MedDRAParseError(
                        f"Invalid PT line: expected at least 2 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                pt_code, pt_name = fields[0], fields[1]

                if not pt_code:
                    raise MedDRAParseError("pt_code must not be empty.", file_name, idx)
                if not pt_code.isdigit() or len(pt_code) != 8:
                    raise MedDRAParseError(
                        "pt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not pt_name:
                    raise MedDRAParseError("pt_name must not be empty.", file_name, idx)
                if len(pt_name) > 255:
                    raise MedDRAParseError(
                        "pt_name exceeds maximum length of 255 characters.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "term",
                    "data": {
                        "code": pt_code,
                        "term_name": pt_name,
                        "level": "PT",
                        "dictionary_version": self.dictionary_version,
                    },
                }

            elif file_type == "hlt":
                if len(fields) < 2:
                    raise MedDRAParseError(
                        f"Invalid HLT line: expected at least 2 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                hlt_code, hlt_name = fields[0], fields[1]

                if not hlt_code:
                    raise MedDRAParseError(
                        "hlt_code must not be empty.", file_name, idx
                    )
                if not hlt_code.isdigit() or len(hlt_code) != 8:
                    raise MedDRAParseError(
                        "hlt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not hlt_name:
                    raise MedDRAParseError(
                        "hlt_name must not be empty.", file_name, idx
                    )
                if len(hlt_name) > 255:
                    raise MedDRAParseError(
                        "hlt_name exceeds maximum length of 255 characters.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "term",
                    "data": {
                        "code": hlt_code,
                        "term_name": hlt_name,
                        "level": "HLT",
                        "dictionary_version": self.dictionary_version,
                    },
                }

            elif file_type == "hlgt":
                if len(fields) < 2:
                    raise MedDRAParseError(
                        f"Invalid HLGT line: expected at least 2 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                hlgt_code, hlgt_name = fields[0], fields[1]

                if not hlgt_code:
                    raise MedDRAParseError(
                        "hlgt_code must not be empty.", file_name, idx
                    )
                if not hlgt_code.isdigit() or len(hlgt_code) != 8:
                    raise MedDRAParseError(
                        "hlgt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not hlgt_name:
                    raise MedDRAParseError(
                        "hlgt_name must not be empty.", file_name, idx
                    )
                if len(hlgt_name) > 255:
                    raise MedDRAParseError(
                        "hlgt_name exceeds maximum length of 255 characters.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "term",
                    "data": {
                        "code": hlgt_code,
                        "term_name": hlgt_name,
                        "level": "HLGT",
                        "dictionary_version": self.dictionary_version,
                    },
                }

            elif file_type == "soc":
                if len(fields) < 2:
                    raise MedDRAParseError(
                        f"Invalid SOC line: expected at least 2 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                soc_code, soc_name = fields[0], fields[1]

                if not soc_code:
                    raise MedDRAParseError(
                        "soc_code must not be empty.", file_name, idx
                    )
                if not soc_code.isdigit() or len(soc_code) != 8:
                    raise MedDRAParseError(
                        "soc_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not soc_name:
                    raise MedDRAParseError(
                        "soc_name must not be empty.", file_name, idx
                    )
                if len(soc_name) > 255:
                    raise MedDRAParseError(
                        "soc_name exceeds maximum length of 255 characters.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "term",
                    "data": {
                        "code": soc_code,
                        "term_name": soc_name,
                        "level": "SOC",
                        "dictionary_version": self.dictionary_version,
                    },
                }

            elif file_type == "mdhier":
                if len(fields) < 9:
                    raise MedDRAParseError(
                        f"Invalid MDHIER line: expected at least 9 fields, got {len(fields)}.",
                        file_name,
                        idx,
                    )
                pt_code, hlt_code, hlgt_code, soc_code = (
                    fields[0],
                    fields[1],
                    fields[2],
                    fields[3],
                )
                primary_soc_flag = fields[8].upper() if fields[8] else ""

                if not pt_code or not pt_code.isdigit() or len(pt_code) != 8:
                    raise MedDRAParseError(
                        "pt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not hlt_code or not hlt_code.isdigit() or len(hlt_code) != 8:
                    raise MedDRAParseError(
                        "hlt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not hlgt_code or not hlgt_code.isdigit() or len(hlgt_code) != 8:
                    raise MedDRAParseError(
                        "hlgt_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if not soc_code or not soc_code.isdigit() or len(soc_code) != 8:
                    raise MedDRAParseError(
                        "soc_code must be an 8-digit numeric string.",
                        file_name,
                        idx,
                    )
                if primary_soc_flag not in {"Y", "N"}:
                    raise MedDRAParseError(
                        "primary_soc_flag must be either 'Y' or 'N'.",
                        file_name,
                        idx,
                    )

                yield {
                    "type": "hierarchy",
                    "data": {
                        "llt_code": "NONE",
                        "pt_code": pt_code,
                        "hlt_code": hlt_code,
                        "hlgt_code": hlgt_code,
                        "soc_code": soc_code,
                        "primary_soc_flag": primary_soc_flag,
                        "dictionary_version": self.dictionary_version,
                    },
                }


def parse_meddra_file(
    file_input: Any,
    dictionary_version: str,
    file_type: str = None,
    file_name: str = None,
    encoding: str = "utf-8",
) -> Iterator[Dict[str, Any]]:
    """Stable public entry point to parse a MedDRA ASCII file streamingly.

    Args:
        file_input: A file path, a file-like object, or an iterable of lines.
        dictionary_version: The version tag of the MedDRA dictionary (e.g. "26.0").
        file_type: One of "llt", "pt", "hlt", "hlgt", "soc", "mdhier". If None,
            it will try to auto-detect from file_name or file_input path.
        file_name: Optional file name for error context.
        encoding: The file encoding to use when reading files (default "utf-8").

    Yields:
        Dict[str, Any]: Parsed MedDRA term or hierarchy record dictionaries.
    """
    parser = MedDRAParser(dictionary_version=dictionary_version, encoding=encoding)
    yield from parser.parse(file_input, file_type=file_type, file_name=file_name)
