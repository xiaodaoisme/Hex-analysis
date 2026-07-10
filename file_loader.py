from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedFile:
    data: bytes
    source_type: str
    base_address: int = 0


def load_file(path: str) -> LoadedFile:
    file_path = Path(path)
    raw = file_path.read_bytes()

    if file_path.suffix.lower() == ".hex":
        parsed = try_parse_intel_hex(raw)
        if parsed is not None:
            return parsed

    return LoadedFile(data=raw, source_type="binary", base_address=0)


def try_parse_intel_hex(raw: bytes) -> LoadedFile | None:
    # Intel HEX is record-oriented text. We only accept the file as HEX when every
    # non-empty line is a valid checksummed record, otherwise callers show raw bytes.
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    memory: dict[int, int] = {}
    upper_address = 0
    saw_eof = False

    for line in lines:
        record = _parse_intel_hex_record(line)
        if record is None:
            return None

        length, address, record_type, payload = record

        if record_type == 0x00:
            absolute = upper_address + address
            for index, value in enumerate(payload):
                memory[absolute + index] = value
        elif record_type == 0x01:
            saw_eof = True
            break
        elif record_type == 0x02:
            if length != 2:
                return None
            upper_address = int.from_bytes(payload, "big") << 4
        elif record_type == 0x04:
            if length != 2:
                return None
            upper_address = int.from_bytes(payload, "big") << 16
        elif record_type in (0x03, 0x05):
            continue
        else:
            return None

    if not saw_eof or not memory:
        return None

    first = min(memory)
    last = max(memory)
    data = bytes(memory.get(address, 0xFF) for address in range(first, last + 1))
    return LoadedFile(data=data, source_type="intel_hex", base_address=first)


def _parse_intel_hex_record(line: str) -> tuple[int, int, int, bytes] | None:
    if not line.startswith(":"):
        return None

    body = line[1:]
    if len(body) < 10 or len(body) % 2 != 0:
        return None

    try:
        record_bytes = bytes.fromhex(body)
    except ValueError:
        return None

    length = record_bytes[0]
    expected_size = 1 + 2 + 1 + length + 1
    if len(record_bytes) != expected_size:
        return None

    if sum(record_bytes) & 0xFF:
        return None

    address = (record_bytes[1] << 8) | record_bytes[2]
    record_type = record_bytes[3]
    payload = record_bytes[4 : 4 + length]
    return length, address, record_type, payload
