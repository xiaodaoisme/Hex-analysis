from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class RenderLine:
    data_index: int
    address: int
    hex_text: str
    ascii_text: str


class ViewerModel:
    def __init__(self, data: bytes = b"", base_address: int = 0) -> None:
        self.data = data
        self.base_address = base_address

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def last_address(self) -> int:
        if not self.data:
            return self.base_address
        return self.base_address + len(self.data) - 1

    def total_lines(self, bytes_per_line: int) -> int:
        if not self.data:
            return 1
        return ceil(len(self.data) / bytes_per_line)

    def line_at(self, line_index: int, bytes_per_line: int) -> RenderLine:
        start = line_index * bytes_per_line
        chunk = self.data[start : start + bytes_per_line]
        address = self.base_address + start
        return RenderLine(
            data_index=start,
            address=address,
            hex_text=" ".join(f"{byte:02X}" for byte in chunk),
            ascii_text=to_ascii(chunk),
        )

    def line_for_data_index(self, data_index: int, bytes_per_line: int) -> int:
        if bytes_per_line <= 0:
            return 0
        return max(0, min(self.total_lines(bytes_per_line) - 1, data_index // bytes_per_line))

    def data_index_for_address(self, address: int) -> int:
        if not self.data:
            return 0
        return max(0, min(len(self.data) - 1, address - self.base_address))


def to_ascii(chunk: bytes) -> str:
    return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
