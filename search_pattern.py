from dataclasses import dataclass


class SearchPatternError(ValueError):
    pass


@dataclass(frozen=True)
class CompiledPattern:
    values: tuple[int, ...]
    masks: tuple[int, ...]

    @property
    def length(self) -> int:
        return len(self.values)


def compile_pattern(text: str) -> CompiledPattern:
    compact = "".join(text.split())
    if not compact:
        raise SearchPatternError("搜索内容不能为空。")

    for char in compact:
        if char not in "0123456789abcdefABCDEF?":
            raise SearchPatternError("搜索内容只能包含 0-9、A-F、? 和空格。")

    if len(compact) % 2:
        raise SearchPatternError("搜索内容必须由偶数个半字节组成，例如 A? 或 0F。")

    values: list[int] = []
    masks: list[int] = []
    for index in range(0, len(compact), 2):
        value, mask = _compile_byte(compact[index : index + 2])
        values.append(value)
        masks.append(mask)

    return CompiledPattern(values=tuple(values), masks=tuple(masks))


def find_matches(data: bytes, pattern: CompiledPattern) -> list[int]:
    # Each compiled byte stores value bits plus a mask, so wildcard nibbles become
    # normal byte-boundary comparisons without trying low-nibble start offsets.
    if pattern.length == 0 or pattern.length > len(data):
        return []

    matches: list[int] = []
    end = len(data) - pattern.length + 1
    for start in range(end):
        for offset, value in enumerate(pattern.values):
            if data[start + offset] & pattern.masks[offset] != value:
                break
        else:
            matches.append(start)
    return matches


def _compile_byte(pair: str) -> tuple[int, int]:
    value = 0
    mask = 0

    for nibble_index, char in enumerate(pair):
        shift = 4 if nibble_index == 0 else 0
        if char == "?":
            continue
        value |= int(char, 16) << shift
        mask |= 0xF << shift

    return value, mask
