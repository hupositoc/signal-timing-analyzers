from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, NumberSetting


class Hla(HighLevelAnalyzer):
    """
    Clock Analyzer

    Input:
      - Low Level Analyzer: SPI
      - Bits per Transfer: 1
      - CLK = SPI Clock
      - DATA = MOSI

    Normal structure:
      - 1 frame = 28 bits
      - Group1 = 14 bits
      - Group2 = 14 bits
      - Internal gap after bit 14: about 3.0 ~ 3.5 us
      - Long gap between frames: about 60.5 ~ 61.5 us

    Tolerant logic:
      - Exact 28bit valid frame -> PASS
      - Small clock interval jitter -> PASS_JITTER_TOLERATED
      - 29~30bit frame caused by short glitch/noise
        -> try removing 1~2 extra bits
        -> if recovered pattern matches allowed pattern -> PASS
      - 27bit frame caused by missed/jittered clock
        -> try inserting 1 missing bit
        -> if recovered pattern matches allowed pattern -> PASS
      - Exact 28bit but DATA_PATTERN_MISMATCH
        -> compare with allowed_patterns by hamming distance
        -> if different bit count <= max_bit_value_jitter_count -> PASS
      - Otherwise -> FAIL
    """

    group1_bits = NumberSetting(min_value=1, max_value=64)
    group2_bits = NumberSetting(min_value=1, max_value=64)

    result_types = {
        "clock_result": {
            "format": (
                "{{data.result}} | Time={{data.start_time_s}}s | "
                "BIN={{data.binary_raw}} | "
                "G1={{data.group1_binary}} | G2={{data.group2_binary}} | "
                "IGAP={{data.internal_gap_us}}us | LGAP={{data.long_gap_us}}us | "
                "IgnoredGlitch={{data.ignored_glitch_count}} | "
                "SplitMerge={{data.split_edge_merge_count}} | "
                "MinGap={{data.min_gap_us}}us | "
                "ShortGap={{data.short_gap_count}} | "
                "{{data.reason}}"
            )
        }
    }

    def __init__(self):
        if self.group1_bits is None:
            self.group1_bits = 14
        if self.group2_bits is None:
            self.group2_bits = 14

        # =========================
        # Frame boundary setting
        # =========================

        self.long_gap_detect_threshold_us = 20.0

        # =========================
        # Normal clock interval
        # =========================

        # 2us급 클럭 기준 정상 범위
        # 약 ±20%
        self.normal_bit_min_us = 1.6
        self.normal_bit_max_us = 2.4

        # =========================
        # Gap criteria
        # =========================

        self.internal_gap_min_us = 2.7
        self.internal_gap_max_us = 4.2

        self.long_gap_min_us = 55.0
        self.long_gap_max_us = 70.0

        # =========================
        # Jitter tolerance settings
        # =========================

        self.enable_jitter_tolerance = True

        # 2us급 클럭 기준 관용 범위
        # 약 ±30~40%
        # 단, 한 프레임 내 1~2개 edge만 허용
        self.jitter_bit_min_us = 0.8
        self.jitter_bit_max_us = 3.2

        self.max_jitter_gap_count = 2

        self.jitter_internal_gap_min_us = 2.2
        self.jitter_internal_gap_max_us = 5.0

        # =========================
        # DATA pattern check
        # =========================

        self.enable_data_pattern_check = True

        self.allowed_patterns = {
            "0000000000001000000000000001",
            "1000000000001000000000000001",
            "0000000000001100000000000001",
        }

        # =========================
        # Extra bit glitch tolerance
        # =========================

        self.enable_glitch_filter = True
        self.max_extra_glitch_bits = 6

        # =========================
        # Gap based glitch candidate scoring
        # =========================
        # 현재 HLA는 SPI Analyzer가 만든 bit frame을 받기 때문에
        # raw clock edge 자체는 직접 볼 수 없다.
        # 대신 SPI-decoded bit 간격(gaps_us)을 이용해서
        # 어떤 bit가 글리치로 끼어든 것인지 우선순위를 계산한다.
        self.enable_gap_based_glitch_scoring = True

        # 이 값보다 짧은 gap 주변 bit는 글리치 후보로 강하게 본다.
        self.gap_short_glitch_us = 0.8

        # bit 하나를 제거했을 때 양쪽 gap이 합쳐져 정상 주기에 가까우면
        # 그 bit를 글리치 후보로 강하게 본다.
        self.gap_merge_min_us = 1.6
        self.gap_merge_max_us = 2.4

        # gap 기반 후보가 너무 적을 때는 전체 조합도 fallback으로 검사한다.
        # 단, 조합 폭발 방지를 위해 extra bit가 큰 경우에는 gap 후보를 우선한다.
        self.enable_full_combination_fallback = True
        self.full_combination_fallback_extra_limit = 4

        # =========================
        # Split edge glitch guard
        # =========================
        # 500 kbit/s 기준 정상 edge 간격 약 2.0us
        # 글리치가 정상 edge의 직전/직후에 붙어
        # 1개의 정상 edge가 2개 edge처럼 쪼개지는 경우 방어한다.
        #
        # 목적:
        #   - PASS 신뢰성 유지
        #   - 자동 최적화 없이 고정 기준으로만 판정
        #   - 쪼개진 edge 2개 중 1개만 정상 edge로 채택

        self.enable_split_edge_glitch_guard = True

        # 0.8us 미만 edge는 단독 정상 edge로 인정하지 않음
        self.glitch_edge_max_us = 0.8

        # 1.6~1.85us는 정상일 수도 있지만,
        # 직후 0.2~0.6us 글리치가 붙어 있을 수 있으므로 pending 처리
        self.early_edge_min_us = 1.6
        self.early_edge_max_us = 1.85

        # pending edge 뒤에 이 이하 간격의 edge가 붙으면 split-tail 후보
        self.split_tail_max_us = 0.6

        # 마지막 정상 edge 기준으로 합산했을 때 이 범위면 정상 edge로 병합 인정
        self.merged_edge_min_us = 1.8
        self.merged_edge_max_us = 2.4

        # =========================
        # Missing bit jitter recovery
        # =========================

        self.enable_missing_bit_recovery = True
        self.max_missing_jitter_bits = 1

        # =========================
        # Bit value jitter correction
        # =========================

        # Exact 28bit인데 일부 bit 값이 지터로 오샘플링된 경우 보정
        self.enable_bit_value_jitter_correction = True

        # 처음에는 1bit만 허용 권장
        # 실제 현장에서 2bit 오샘플링이 명확하면 2로 확대 가능
        self.max_bit_value_jitter_count = 1

        # =========================
        # Internal state
        # =========================

        self.complete_frame_seen = False
        self.frame_no = 0
        self.zero_time = None

        self.reset_frame()

    def reset_frame(self):
        self.bits = []
        self.gaps_us = []

        self.frame_start_time = None
        self.last_bit_time = None
        self.last_frame_end_time = None

        # Split edge glitch guard state
        self.pending_edge_frame = None
        self.pending_edge_bit = None
        self.pending_edge_gap_us = None
        self.pending_edge_time = None

        self.ignored_glitch_count = 0
        self.split_edge_merge_count = 0

        # try_remove_glitch_bits()에서 extra bit 제거 후 재구성한 gap 배열
        self.last_glitch_corrected_gaps = None

    def clear_pending_edge(self):
        self.pending_edge_frame = None
        self.pending_edge_bit = None
        self.pending_edge_gap_us = None
        self.pending_edge_time = None

    def accept_bit_edge(self, frame, bit, gap_us):
        """
        실제 정상 edge로 채택된 경우에만 bit/gap을 반영한다.
        글리치로 판단된 edge는 이 함수를 통과하지 않는다.
        """

        self.gaps_us.append(round(gap_us, 3))
        self.bits.append(bit)

        self.last_bit_time = frame.start_time
        self.last_frame_end_time = frame.end_time

    def store_pending_edge(self, frame, bit, gap_us):
        """
        1.6~1.85us처럼 약간 빠른 edge는 바로 확정하지 않고 보류한다.
        다음 edge가 짧게 붙으면 split edge로 판단할 수 있다.
        """

        self.pending_edge_frame = frame
        self.pending_edge_bit = bit
        self.pending_edge_gap_us = gap_us
        self.pending_edge_time = frame.start_time

    def extract_bit(self, frame):
        """
        Extract 1 bit from the input analyzer frame.

        Compatible inputs:
          1) Saleae SPI Analyzer style:
             - mosi
             - miso
             - data

          2) Custom SSI LLA style:
             - value
             - Raw Value
             - DATA

        SSI LLA may display one frame as strings such as:
          - "1"
          - "0"
          - "0x1"
          - "1 / 1 bit / Edge=Rising / Gap=2000 ns"

        This function always returns only one bit: 0 or 1.
        """
        data = frame.data

        value = None

        # 1. Saleae SPI Analyzer compatible keys
        if "mosi" in data:
            value = data["mosi"]
        elif "miso" in data:
            value = data["miso"]
        elif "data" in data:
            value = data["data"]

        # 2. Custom SSI LLA displayed/raw value keys
        elif "value" in data:
            value = data["value"]
        elif "Raw Value" in data:
            value = data["Raw Value"]
        elif "DATA" in data:
            value = data["DATA"]

        if value is None:
            return None

        # bytes case
        if isinstance(value, bytes):
            if len(value) == 0:
                return None
            return value[0] & 0x01

        # int case
        if isinstance(value, int):
            return value & 0x01

        # string case
        text = str(value).strip()

        if text == "":
            return None

        # Custom SSI detail string case:
        #   "1 / 1 bit / Edge=Rising / Gap=2000 ns"
        # Take the first token before "/".
        if "/" in text:
            text = text.split("/", 1)[0].strip()

        # Remove possible label prefix.
        if text.startswith("DATA="):
            text = text.replace("DATA=", "", 1).strip()

        # Binary string case
        if text.startswith("0b") or text.startswith("0B"):
            try:
                return int(text, 2) & 0x01
            except Exception:
                return None

        # Hex string case
        if text.startswith("0x") or text.startswith("0X"):
            try:
                return int(text, 16) & 0x01
            except Exception:
                return None

        # Decimal / plain 0 or 1 case
        try:
            return int(text) & 0x01
        except Exception:
            return None

    def bits_to_string(self, bits):
        return "".join(str(b) for b in bits)

    def string_to_bits(self, binary):
        return [int(ch) for ch in binary]

    def start_new_frame(self, frame, bit):
        if self.zero_time is None:
            self.zero_time = frame.start_time

        self.bits = [bit]
        self.gaps_us = []

        self.frame_start_time = frame.start_time
        self.last_bit_time = frame.start_time
        self.last_frame_end_time = frame.end_time

        self.clear_pending_edge()
        self.ignored_glitch_count = 0
        self.split_edge_merge_count = 0

        # try_remove_glitch_bits()에서 extra bit 제거 후 재구성한 gap 배열
        self.last_glitch_corrected_gaps = None

    def time_to_relative_s(self, t, fallback_t):
        if self.zero_time is None:
            self.zero_time = fallback_t

        if t is None:
            return float(fallback_t - self.zero_time)

        return float(t - self.zero_time)

    # ============================================================
    # Gap based glitch scoring helpers
    # ============================================================

    def get_gap_summary(self):
        if not self.gaps_us:
            return 0.0, 0.0, 0, 0, ""

        min_gap = min(self.gaps_us)
        max_gap = max(self.gaps_us)

        short_count = 0
        early_count = 0

        for gap in self.gaps_us:
            if gap < self.gap_short_glitch_us:
                short_count += 1
            if self.early_edge_min_us <= gap <= self.early_edge_max_us:
                early_count += 1

        # Excel/CSV에서 확인 가능하도록 전체 gap을 문자열로 남긴다.
        # 너무 길어지는 것을 방지하기 위해 80개까지만 표시한다.
        gap_items = []
        limit = 80
        for i, gap in enumerate(self.gaps_us[:limit]):
            gap_items.append(str(i) + ":" + str(round(gap, 3)))

        if len(self.gaps_us) > limit:
            gap_items.append("...")

        gaps_text = ";".join(gap_items)

        return min_gap, max_gap, short_count, early_count, gaps_text

    def get_remove_index_timing_score(self, remove_idx, gaps):
        """
        특정 bit index를 제거했을 때 timing 관점에서 얼마나 글리치다운지 점수화한다.
        낮은 점수일수록 글리치 후보 가능성이 높다.

        bit index와 gap index의 관계:
          gap[0] = bit0 -> bit1 간격
          gap[i-1] = bit(i-1) -> bit(i) 간격
        """

        score = 1000.0

        prev_gap = None
        next_gap = None

        if remove_idx > 0 and (remove_idx - 1) < len(gaps):
            prev_gap = gaps[remove_idx - 1]

        if remove_idx < len(gaps):
            next_gap = gaps[remove_idx]

        local_scores = []

        # 짧은 gap 바로 옆 bit는 글리치 후보로 강하게 본다.
        if prev_gap is not None:
            if prev_gap < self.gap_short_glitch_us:
                local_scores.append(0.0 + prev_gap)
            elif prev_gap < self.normal_bit_min_us:
                local_scores.append(20.0 + prev_gap)

        if next_gap is not None:
            if next_gap < self.gap_short_glitch_us:
                local_scores.append(0.0 + next_gap)
            elif next_gap < self.normal_bit_min_us:
                local_scores.append(20.0 + next_gap)

        # bit 하나를 제거했을 때 양쪽 gap이 합쳐져 정상 주기 범위면
        # 이 bit가 끼어든 글리치일 가능성이 높다.
        if prev_gap is not None and next_gap is not None:
            merged = prev_gap + next_gap
            if self.gap_merge_min_us <= merged <= self.gap_merge_max_us:
                center = (self.gap_merge_min_us + self.gap_merge_max_us) / 2.0
                local_scores.append(abs(merged - center))
            elif self.jitter_bit_min_us <= merged <= self.jitter_bit_max_us:
                center = (self.gap_merge_min_us + self.gap_merge_max_us) / 2.0
                local_scores.append(30.0 + abs(merged - center))

        if local_scores:
            score = min(local_scores)

        return score

    def get_remove_set_timing_score(self, remove_indices, gaps):
        if not self.enable_gap_based_glitch_scoring:
            return 0.0

        if not remove_indices:
            return 9999.0

        score = 0.0
        for idx in remove_indices:
            score += self.get_remove_index_timing_score(idx, gaps)

        return round(score, 3)

    def get_gap_based_candidate_indices(self, bit_count, extra_count):
        """
        gaps_us를 이용해 제거 후보 index를 만든다.
        후보가 부족하면 전체 index를 반환한다.
        """

        if not self.enable_gap_based_glitch_scoring:
            return list(range(bit_count))

        candidates = set()

        # 짧은 gap 주변 bit를 후보로 추가한다.
        for gap_idx, gap in enumerate(self.gaps_us):
            if gap < self.gap_short_glitch_us:
                candidates.add(gap_idx)
                candidates.add(gap_idx + 1)
            elif gap < self.normal_bit_min_us:
                candidates.add(gap_idx)
                candidates.add(gap_idx + 1)

        # 특정 bit를 제거했을 때 양쪽 gap이 정상 주기로 합쳐지면 후보로 추가한다.
        for bit_idx in range(1, bit_count - 1):
            prev_gap = self.gaps_us[bit_idx - 1] if bit_idx - 1 < len(self.gaps_us) else None
            next_gap = self.gaps_us[bit_idx] if bit_idx < len(self.gaps_us) else None

            if prev_gap is None or next_gap is None:
                continue

            merged = prev_gap + next_gap
            if self.gap_merge_min_us <= merged <= self.gap_merge_max_us:
                candidates.add(bit_idx)

        # 후보가 너무 적으면 전체 후보를 사용한다.
        if len(candidates) < extra_count:
            return list(range(bit_count))

        # timing score가 좋은 순서로 정렬한다.
        sorted_candidates = sorted(
            list(candidates),
            key=lambda idx: self.get_remove_index_timing_score(idx, self.gaps_us),
        )

        return sorted_candidates

    def build_corrected_gaps_after_remove(self, remove_indices):
        """
        bit index 제거 후 gap 배열을 재구성한다.
        예: 가운데 bit를 제거하면 양쪽 gap이 합쳐진다.
        """

        if not self.gaps_us:
            return []

        remove_set = set(remove_indices)

        # frame 시작을 0으로 두고 상대 edge time을 재구성한다.
        times = [0.0]
        for gap in self.gaps_us:
            times.append(times[-1] + float(gap))

        kept_times = []
        for idx, t in enumerate(times):
            if idx not in remove_set:
                kept_times.append(t)

        corrected_gaps = []
        for i in range(1, len(kept_times)):
            corrected_gaps.append(round(kept_times[i] - kept_times[i - 1], 3))

        return corrected_gaps

    # ============================================================
    # Extra bit recovery
    # ============================================================

    def try_remove_glitch_bits(self, bits, expected_total):
        """
        Extra bit가 생긴 경우, 초과 bit 개수만큼 제거 조합을 시도한다.

        v5 변경점:
          - 제거 후보를 단순 패턴 기준으로만 보지 않고 gaps_us 기반 timing score를 함께 본다.
          - 짧은 gap 주변 bit, 제거 시 양쪽 gap이 정상 주기로 합쳐지는 bit를 우선 제거 후보로 본다.
          - exact match를 최우선으로 하되, exact 후보가 여러 개면 timing score가 가장 좋은 후보를 선택한다.
          - exact match가 없으면 Hamming distance + timing score 기준으로 최선 후보를 선택한다.
        """

        if not self.enable_glitch_filter:
            return None, "GLITCH_FILTER_DISABLED"

        bit_count = len(bits)

        if bit_count <= expected_total:
            return None, "NO_EXTRA_BITS"

        extra_count = bit_count - expected_total

        if extra_count > self.max_extra_glitch_bits:
            return None, (
                "TOO_MANY_EXTRA_BITS_RAW_"
                + str(bit_count)
                + "_EXPECTED_"
                + str(expected_total)
                + "_EXTRA_"
                + str(extra_count)
                + "_MAX_"
                + str(self.max_extra_glitch_bits)
            )

        if not self.enable_data_pattern_check:
            return None, "PATTERN_CHECK_DISABLED_FOR_GLITCH_FILTER"

        from itertools import combinations

        candidate_indices = self.get_gap_based_candidate_indices(bit_count, extra_count)

        # gap 후보 기반 조합을 먼저 검사한다.
        candidate_sets = []
        seen_sets = set()

        if len(candidate_indices) >= extra_count:
            for remove_indices in combinations(candidate_indices, extra_count):
                remove_indices = tuple(sorted(remove_indices))
                if remove_indices not in seen_sets:
                    seen_sets.add(remove_indices)
                    candidate_sets.append(remove_indices)

        # 후보가 없거나, extra bit가 비교적 적으면 전체 조합도 fallback으로 검사한다.
        if (
            self.enable_full_combination_fallback
            and extra_count <= self.full_combination_fallback_extra_limit
        ):
            for remove_indices in combinations(range(bit_count), extra_count):
                remove_indices = tuple(sorted(remove_indices))
                if remove_indices not in seen_sets:
                    seen_sets.add(remove_indices)
                    candidate_sets.append(remove_indices)

        if not candidate_sets:
            return None, (
                "GLITCH_FILTER_NO_CANDIDATE_SET_RAW_"
                + str(bit_count)
                + "_EXPECTED_"
                + str(expected_total)
                + "_EXTRA_"
                + str(extra_count)
            )

        exact_matches = []
        hamming_matches = []

        best_distance = None
        best_remove_idx_text = ""
        best_diff_idx = []
        best_pattern = ""
        best_timing_score = None

        for remove_indices in candidate_sets:
            remove_set = set(remove_indices)

            corrected = []
            for idx, bit in enumerate(bits):
                if idx not in remove_set:
                    corrected.append(bit)

            corrected_binary = self.bits_to_string(corrected)
            idx_text = "_".join(str(x) for x in remove_indices)
            timing_score = self.get_remove_set_timing_score(remove_indices, self.gaps_us)

            if corrected_binary in self.allowed_patterns:
                exact_matches.append(
                    (timing_score, remove_indices, idx_text, corrected, corrected_binary)
                )
                continue

            if not self.enable_bit_value_jitter_correction:
                continue

            if len(corrected_binary) != expected_total:
                continue

            for pattern in self.allowed_patterns:
                if len(pattern) != expected_total:
                    continue

                diff_idx = []
                for i in range(expected_total):
                    if corrected_binary[i] != pattern[i]:
                        diff_idx.append(i)

                distance = len(diff_idx)

                if (
                    best_distance is None
                    or distance < best_distance
                    or (
                        distance == best_distance
                        and (
                            best_timing_score is None
                            or timing_score < best_timing_score
                        )
                    )
                ):
                    best_distance = distance
                    best_remove_idx_text = idx_text
                    best_diff_idx = diff_idx
                    best_pattern = pattern
                    best_timing_score = timing_score

                if distance <= self.max_bit_value_jitter_count:
                    hamming_matches.append(
                        (
                            distance,
                            timing_score,
                            remove_indices,
                            idx_text,
                            pattern,
                            diff_idx,
                        )
                    )

        # ------------------------------------------------------------
        # 1st priority: exact match + best timing score
        # ------------------------------------------------------------
        if exact_matches:
            exact_matches.sort(key=lambda x: (x[0], x[2]))
            timing_score, remove_indices, idx_text, corrected, corrected_binary = exact_matches[0]

            self.last_glitch_corrected_gaps = self.build_corrected_gaps_after_remove(
                remove_indices
            )

            return corrected, (
                "PASS_GLITCH_FILTERED_REMOVE_"
                + str(extra_count)
                + "BITS_IDX_"
                + str(idx_text)
                + "_EXACT_TSCORE_"
                + str(timing_score)
            )

        # ------------------------------------------------------------
        # 2nd priority: hamming within limit + best timing score
        # ------------------------------------------------------------
        if hamming_matches:
            hamming_matches.sort(key=lambda x: (x[0], x[1], x[3]))
            (
                distance,
                timing_score,
                remove_indices,
                idx_text,
                pattern,
                diff_idx,
            ) = hamming_matches[0]

            corrected_bits = self.string_to_bits(pattern)
            diff_text = "_".join(str(x) for x in diff_idx)

            self.last_glitch_corrected_gaps = self.build_corrected_gaps_after_remove(
                remove_indices
            )

            return corrected_bits, (
                "PASS_GLITCH_FILTERED_REMOVE_"
                + str(extra_count)
                + "BITS_IDX_"
                + str(idx_text)
                + "_HAMMING_"
                + str(distance)
                + "_DIFF_IDX_"
                + str(diff_text)
                + "_TSCORE_"
                + str(timing_score)
            )

        if not self.enable_bit_value_jitter_correction:
            return None, (
                "GLITCH_FILTER_NO_MATCH_REMOVE_"
                + str(extra_count)
                + "BITS_RAW_"
                + str(bit_count)
                + "_EXPECTED_"
                + str(expected_total)
                + "_HAMMING_DISABLED"
            )

        diff_text = "_".join(str(x) for x in best_diff_idx)

        return None, (
            "GLITCH_FILTER_NO_MATCH_REMOVE_"
            + str(extra_count)
            + "BITS_RAW_"
            + str(bit_count)
            + "_EXPECTED_"
            + str(expected_total)
            + "_BEST_HAMMING_"
            + str(best_distance)
            + "_REMOVE_IDX_"
            + str(best_remove_idx_text)
            + "_DIFF_IDX_"
            + str(diff_text)
            + "_TSCORE_"
            + str(best_timing_score)
        )

    # ============================================================
    # Missing bit recovery
    # ============================================================

    def try_insert_missing_jitter_bit(self, bits, expected_total):
        """
        27bit처럼 1bit가 누락된 것으로 보이는 경우,
        0 또는 1을 각 위치에 삽입해 allowed pattern과 일치하는지 확인한다.
        """

        if not self.enable_missing_bit_recovery:
            return None, "MISSING_BIT_RECOVERY_DISABLED"

        bit_count = len(bits)

        if bit_count >= expected_total:
            return None, "NO_MISSING_BITS"

        missing_count = expected_total - bit_count

        if missing_count > self.max_missing_jitter_bits:
            return None, "TOO_MANY_MISSING_BITS"

        if not self.enable_data_pattern_check:
            return None, "PATTERN_CHECK_DISABLED_FOR_MISSING_BIT_RECOVERY"

        if missing_count == 1:
            for insert_idx in range(expected_total + 1):
                for insert_bit in [0, 1]:
                    corrected = (
                        bits[:insert_idx]
                        + [insert_bit]
                        + bits[insert_idx:]
                    )

                    corrected_binary = self.bits_to_string(corrected)

                    if corrected_binary in self.allowed_patterns:
                        return corrected, (
                            "PASS_JITTER_INSERTED_1BIT_IDX_"
                            + str(insert_idx)
                            + "_VALUE_"
                            + str(insert_bit)
                        )

        return None, "MISSING_BIT_RECOVERY_NO_MATCH"

    # ============================================================
    # Bit value jitter correction by Hamming distance
    # ============================================================

    def try_correct_bit_value_jitter_by_hamming(self, bits, expected_total):
        """
        Exact 28bit인데 DATA_PATTERN_MISMATCH가 발생한 경우,
        allowed_patterns와 비교하여 가장 가까운 기준 패턴을 찾는다.

        Hamming distance가 max_bit_value_jitter_count 이하이면
        지터성 오샘플링으로 보고 해당 기준 패턴으로 보정 PASS 처리한다.

        예:
          RAW:
            1000000000000000000000000001

          REF:
            1000000000001000000000000001

          DIFF_IDX:
            [13]

          HAMMING:
            1

          RESULT:
            PASS_BIT_VALUE_JITTER_CORRECTED_HAMMING_1_IDX_13
        """

        if not self.enable_bit_value_jitter_correction:
            return None, "BIT_VALUE_JITTER_CORRECTION_DISABLED", [], ""

        if len(bits) != expected_total:
            return None, "NOT_EXACT_BIT_COUNT", [], ""

        if not self.enable_data_pattern_check:
            return None, "PATTERN_CHECK_DISABLED_FOR_BIT_VALUE_CORRECTION", [], ""

        raw_binary = self.bits_to_string(bits)

        best_pattern = None
        best_diff_idx = []
        best_distance = None

        for pattern in self.allowed_patterns:
            if len(pattern) != expected_total:
                continue

            diff_idx = []

            for i in range(expected_total):
                if raw_binary[i] != pattern[i]:
                    diff_idx.append(i)

            distance = len(diff_idx)

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_pattern = pattern
                best_diff_idx = diff_idx

        if best_pattern is None:
            return None, "NO_REFERENCE_PATTERN", [], ""

        if best_distance <= self.max_bit_value_jitter_count:
            corrected_bits = self.string_to_bits(best_pattern)

            idx_text = ",".join(str(x) for x in best_diff_idx)

            return (
                corrected_bits,
                "PASS_BIT_VALUE_JITTER_CORRECTED_HAMMING_"
                + str(best_distance)
                + "_IDX_"
                + idx_text,
                best_diff_idx,
                best_pattern,
            )

        idx_text = ",".join(str(x) for x in best_diff_idx)

        return (
            None,
            "BIT_VALUE_JITTER_CORRECTION_FAILED_HAMMING_"
            + str(best_distance)
            + "_IDX_"
            + idx_text
            + "_NEAREST_"
            + str(best_pattern),
            best_diff_idx,
            best_pattern,
        )

    # ============================================================
    # Jitter timing check
    # ============================================================

    def check_jitter_tolerable(
        self,
        expected_group1,
        internal_gap_us,
    ):
        """
        정상 범위는 벗어났지만 실제 장비에서 보정 가능한 수준인지 판단한다.

        기준:
          - normal bit interval: 1.6 ~ 2.4us
          - jitter tolerated interval: 0.8 ~ 3.2us
          - max jitter gap count: 2
          - internal gap tolerated: 2.2 ~ 5.0us
        """

        if not self.enable_jitter_tolerance:
            return False, "JITTER_TOLERANCE_DISABLED"

        jitter_count = 0
        severe_count = 0

        for i, gap in enumerate(self.gaps_us):
            # internal gap 위치는 별도 판단
            if i == expected_group1 - 1:
                continue

            if self.normal_bit_min_us <= gap <= self.normal_bit_max_us:
                continue

            if self.jitter_bit_min_us <= gap <= self.jitter_bit_max_us:
                jitter_count += 1
            else:
                severe_count += 1

        if severe_count > 0:
            return False, "SEVERE_CLK_INTERVAL_ERROR"

        if jitter_count > self.max_jitter_gap_count:
            return False, "TOO_MANY_JITTER_GAPS_" + str(jitter_count)

        if not (
            self.jitter_internal_gap_min_us
            <= internal_gap_us
            <= self.jitter_internal_gap_max_us
        ):
            return False, "INTERNAL_GAP_SEVERE_OUT_OF_RANGE"

        if jitter_count > 0:
            return True, "PASS_JITTER_TOLERATED_GAPS_" + str(jitter_count)

        if not (
            self.internal_gap_min_us
            <= internal_gap_us
            <= self.internal_gap_max_us
        ):
            return True, "PASS_INTERNAL_GAP_JITTER_TOLERATED"

        return False, "NO_JITTER_FOUND"

    # ============================================================
    # Result frame
    # ============================================================

    def make_result_frame(
        self,
        frame,
        result,
        reason,
        binary_raw,
        group1_binary,
        group2_binary,
        total_count,
        internal_gap_us,
        long_gap_us,
        frame_duration_us,
        original_binary_raw="",
        original_total_count=0,
        nearest_pattern="",
        diff_indices=None,
    ):
        raw_value = int(binary_raw, 2) if binary_raw else 0

        if diff_indices is None:
            diff_indices = []

        diff_indices_text = ",".join(str(x) for x in diff_indices)

        min_gap_us, max_gap_us, short_gap_count, early_gap_count, gaps_text = (
            self.get_gap_summary()
        )

        self.frame_no += 1

        start_time_s = self.time_to_relative_s(
            self.frame_start_time,
            frame.start_time,
        )

        end_time_s = self.time_to_relative_s(
            self.last_frame_end_time,
            frame.end_time,
        )

        start_time_us = start_time_s * 1_000_000.0
        end_time_us = end_time_s * 1_000_000.0

        print(
            "Start="
            + str(round(start_time_s, 9))
            + "s"
            + " | Start_us="
            + str(round(start_time_us, 3))
            + "us"
            + " | End="
            + str(round(end_time_s, 9))
            + "s"
            + " | End_us="
            + str(round(end_time_us, 3))
            + "us"
            + " | Frame="
            + str(self.frame_no)
            + " | Result="
            + str(result)
            + " | Reason="
            + str(reason)
            + " | BIN="
            + str(binary_raw)
            + " | HEX=0x"
            + format(raw_value, "X")
            + " | G1="
            + str(group1_binary)
            + " | G2="
            + str(group2_binary)
            + " | Bits="
            + str(total_count)
            + " | OriginalBits="
            + str(original_total_count)
            + " | OriginalBIN="
            + str(original_binary_raw)
            + " | NearestPattern="
            + str(nearest_pattern)
            + " | DiffIdx="
            + str(diff_indices_text)
            + " | IgnoredGlitch="
            + str(self.ignored_glitch_count)
            + " | SplitMerge="
            + str(self.split_edge_merge_count)
            + " | MinGap="
            + str(round(min_gap_us, 3))
            + "us"
            + " | MaxGap="
            + str(round(max_gap_us, 3))
            + "us"
            + " | ShortGapCount="
            + str(short_gap_count)
            + " | EarlyGapCount="
            + str(early_gap_count)
            + " | GAPS="
            + str(gaps_text)
            + " | IGAP="
            + str(round(internal_gap_us, 3))
            + "us"
            + " | LGAP="
            + str(round(long_gap_us, 3))
            + "us"
            + " | Duration="
            + str(round(frame_duration_us, 3))
            + "us"
        )

        return AnalyzerFrame(
            "clock_result",
            self.frame_start_time if self.frame_start_time is not None else frame.start_time,
            self.last_frame_end_time if self.last_frame_end_time is not None else frame.end_time,
            {
                "result": str(result),
                "reason": str(reason),

                "frame_no": int(self.frame_no),

                "start_time_s": float(round(start_time_s, 9)),
                "start_time_us": float(round(start_time_us, 3)),
                "end_time_s": float(round(end_time_s, 9)),
                "end_time_us": float(round(end_time_us, 3)),

                "binary_raw": str(binary_raw),
                "hex": "0x" + format(raw_value, "X"),
                "dec": int(raw_value),

                "group1_binary": str(group1_binary),
                "group2_binary": str(group2_binary),

                "group1_count": int(len(group1_binary)),
                "group2_count": int(len(group2_binary)),
                "total_count": int(total_count),

                "original_binary_raw": str(original_binary_raw),
                "original_total_count": int(original_total_count),

                "nearest_pattern": str(nearest_pattern),
                "diff_indices": str(diff_indices_text),

                "ignored_glitch_count": int(self.ignored_glitch_count),
                "split_edge_merge_count": int(self.split_edge_merge_count),

                "min_gap_us": float(round(min_gap_us, 3)),
                "max_gap_us": float(round(max_gap_us, 3)),
                "short_gap_count": int(short_gap_count),
                "early_gap_count": int(early_gap_count),
                "gaps_us": str(gaps_text),

                "internal_gap_us": float(round(internal_gap_us, 3)),
                "long_gap_us": float(round(long_gap_us, 3)),
                "frame_duration_us": float(round(frame_duration_us, 3)),
            },
        )

    # ============================================================
    # Normal timing check
    # ============================================================

    def check_timing_normal(
        self,
        binary_raw,
        group1_binary,
        group2_binary,
        total_count,
        internal_gap_us,
        long_gap_us,
        frame_duration_us,
        frame,
    ):
        expected_group1 = int(self.group1_bits)

        # Long gap은 프레임 경계라서 엄격하게 유지
        if not (self.long_gap_min_us <= long_gap_us <= self.long_gap_max_us):
            return self.make_result_frame(
                frame,
                "FAIL",
                "LONG_GAP_OUT_OF_RANGE",
                binary_raw,
                group1_binary,
                group2_binary,
                total_count,
                internal_gap_us,
                long_gap_us,
                frame_duration_us,
                binary_raw,
                total_count,
            )

        timing_fail_reason = None

        if not (
            self.internal_gap_min_us
            <= internal_gap_us
            <= self.internal_gap_max_us
        ):
            timing_fail_reason = "INTERNAL_GAP_OUT_OF_RANGE"

        for i, gap in enumerate(self.gaps_us):
            if i == expected_group1 - 1:
                continue

            if not (self.normal_bit_min_us <= gap <= self.normal_bit_max_us):
                timing_fail_reason = "CLK_INTERVAL_OUT_OF_RANGE"
                break

        if timing_fail_reason is None:
            return None

        # 바로 FAIL하지 않고, 실제 장비 보정 가능 수준인지 확인
        jitter_ok, jitter_reason = self.check_jitter_tolerable(
            expected_group1,
            internal_gap_us,
        )

        if jitter_ok:
            return self.make_result_frame(
                frame,
                "PASS",
                jitter_reason,
                binary_raw,
                group1_binary,
                group2_binary,
                total_count,
                internal_gap_us,
                long_gap_us,
                frame_duration_us,
                binary_raw,
                total_count,
            )

        return self.make_result_frame(
            frame,
            "FAIL",
            timing_fail_reason + "_" + jitter_reason,
            binary_raw,
            group1_binary,
            group2_binary,
            total_count,
            internal_gap_us,
            long_gap_us,
            frame_duration_us,
            binary_raw,
            total_count,
        )

    # ============================================================
    # Finalize frame
    # ============================================================

    def finalize_frame(self, frame, long_gap_us):
        expected_group1 = int(self.group1_bits)
        expected_group2 = int(self.group2_bits)
        expected_total = expected_group1 + expected_group2

        total_count = len(self.bits)
        binary_raw = self.bits_to_string(self.bits)

        frame_duration_us = 0.0
        if self.frame_start_time is not None and self.last_frame_end_time is not None:
            frame_duration_us = float(
                self.last_frame_end_time - self.frame_start_time
            ) * 1_000_000.0

        # 첫 완성 프레임 이전의 불완전 프레임은 무시
        if not self.complete_frame_seen and total_count < expected_total:
            return None

        # ============================================================
        # Case A. Exact expected bit count
        # ============================================================

        if total_count == expected_total:
            self.complete_frame_seen = True

            group1_bits = self.bits[:expected_group1]
            group2_bits = self.bits[expected_group1:]

            group1_binary = self.bits_to_string(group1_bits)
            group2_binary = self.bits_to_string(group2_bits)

            if len(self.gaps_us) >= expected_group1:
                internal_gap_us = self.gaps_us[expected_group1 - 1]
            else:
                return self.make_result_frame(
                    frame,
                    "FAIL",
                    "INTERNAL_GAP_MISSING",
                    binary_raw,
                    group1_binary,
                    group2_binary,
                    total_count,
                    0.0,
                    long_gap_us,
                    frame_duration_us,
                    binary_raw,
                    total_count,
                )

            timing_result = self.check_timing_normal(
                binary_raw,
                group1_binary,
                group2_binary,
                total_count,
                internal_gap_us,
                long_gap_us,
                frame_duration_us,
                frame,
            )

            if timing_result is not None:
                return timing_result

            # DATA pattern check
            if self.enable_data_pattern_check:
                if binary_raw not in self.allowed_patterns:

                    corrected_bits, bit_value_reason, diff_idx, nearest_pattern = (
                        self.try_correct_bit_value_jitter_by_hamming(
                            self.bits,
                            expected_total,
                        )
                    )

                    if corrected_bits is not None:
                        corrected_binary = self.bits_to_string(corrected_bits)

                        corrected_group1_bits = corrected_bits[:expected_group1]
                        corrected_group2_bits = corrected_bits[expected_group1:]

                        corrected_group1_binary = self.bits_to_string(
                            corrected_group1_bits
                        )
                        corrected_group2_binary = self.bits_to_string(
                            corrected_group2_bits
                        )

                        return self.make_result_frame(
                            frame,
                            "PASS",
                            bit_value_reason,
                            corrected_binary,
                            corrected_group1_binary,
                            corrected_group2_binary,
                            expected_total,
                            internal_gap_us,
                            long_gap_us,
                            frame_duration_us,
                            binary_raw,
                            total_count,
                            nearest_pattern,
                            diff_idx,
                        )

                    return self.make_result_frame(
                        frame,
                        "FAIL",
                        "DATA_PATTERN_MISMATCH_" + bit_value_reason,
                        binary_raw,
                        group1_binary,
                        group2_binary,
                        total_count,
                        internal_gap_us,
                        long_gap_us,
                        frame_duration_us,
                        binary_raw,
                        total_count,
                        nearest_pattern,
                        diff_idx,
                    )

            return self.make_result_frame(
                frame,
                "PASS",
                "OK",
                binary_raw,
                group1_binary,
                group2_binary,
                total_count,
                internal_gap_us,
                long_gap_us,
                frame_duration_us,
                binary_raw,
                total_count,
            )

        # ============================================================
        # Case B. Extra bits exist
        # ============================================================

        if total_count > expected_total:
            corrected_bits, glitch_reason = self.try_remove_glitch_bits(
                self.bits,
                expected_total,
            )

            if corrected_bits is not None:
                self.complete_frame_seen = True

                corrected_binary = self.bits_to_string(corrected_bits)

                group1_bits = corrected_bits[:expected_group1]
                group2_bits = corrected_bits[expected_group1:]

                group1_binary = self.bits_to_string(group1_bits)
                group2_binary = self.bits_to_string(group2_bits)

                internal_gap_us = 0.0

                # extra bit 제거 후 재구성된 gap 배열이 있으면 그 기준으로 internal gap 산정
                corrected_gaps_for_timing = self.last_glitch_corrected_gaps

                if (
                    corrected_gaps_for_timing is not None
                    and len(corrected_gaps_for_timing) >= expected_group1
                ):
                    internal_gap_us = corrected_gaps_for_timing[expected_group1 - 1]
                elif len(self.gaps_us) >= expected_group1:
                    internal_gap_us = self.gaps_us[expected_group1 - 1]

                if not (self.long_gap_min_us <= long_gap_us <= self.long_gap_max_us):
                    return self.make_result_frame(
                        frame,
                        "FAIL",
                        "LONG_GAP_OUT_OF_RANGE_AFTER_GLITCH_FILTER",
                        corrected_binary,
                        group1_binary,
                        group2_binary,
                        expected_total,
                        internal_gap_us,
                        long_gap_us,
                        frame_duration_us,
                        binary_raw,
                        total_count,
                    )

                return self.make_result_frame(
                    frame,
                    "PASS",
                    glitch_reason,
                    corrected_binary,
                    group1_binary,
                    group2_binary,
                    expected_total,
                    internal_gap_us,
                    long_gap_us,
                    frame_duration_us,
                    binary_raw,
                    total_count,
                )

            return self.make_result_frame(
                frame,
                "FAIL",
                "BIT_COUNT_ERROR_" + glitch_reason,
                binary_raw,
                "",
                "",
                total_count,
                0.0,
                long_gap_us,
                frame_duration_us,
                binary_raw,
                total_count,
            )

        # ============================================================
        # Case C. Missing bits exist
        # ============================================================

        if total_count < expected_total:
            corrected_bits, missing_reason = self.try_insert_missing_jitter_bit(
                self.bits,
                expected_total,
            )

            if corrected_bits is not None:
                self.complete_frame_seen = True

                corrected_binary = self.bits_to_string(corrected_bits)

                group1_bits = corrected_bits[:expected_group1]
                group2_bits = corrected_bits[expected_group1:]

                group1_binary = self.bits_to_string(group1_bits)
                group2_binary = self.bits_to_string(group2_bits)

                internal_gap_us = 0.0
                if len(self.gaps_us) >= expected_group1:
                    internal_gap_us = self.gaps_us[expected_group1 - 1]

                if not (self.long_gap_min_us <= long_gap_us <= self.long_gap_max_us):
                    return self.make_result_frame(
                        frame,
                        "FAIL",
                        "LONG_GAP_OUT_OF_RANGE_AFTER_MISSING_BIT_RECOVERY",
                        corrected_binary,
                        group1_binary,
                        group2_binary,
                        expected_total,
                        internal_gap_us,
                        long_gap_us,
                        frame_duration_us,
                        binary_raw,
                        total_count,
                    )

                return self.make_result_frame(
                    frame,
                    "PASS",
                    missing_reason,
                    corrected_binary,
                    group1_binary,
                    group2_binary,
                    expected_total,
                    internal_gap_us,
                    long_gap_us,
                    frame_duration_us,
                    binary_raw,
                    total_count,
                )

            return self.make_result_frame(
                frame,
                "FAIL",
                "BIT_COUNT_ERROR_MISSING_BITS_" + missing_reason,
                binary_raw,
                "",
                "",
                total_count,
                0.0,
                long_gap_us,
                frame_duration_us,
                binary_raw,
                total_count,
            )

        return None

    # ============================================================
    # Main decode
    # ============================================================

    def decode(self, frame: AnalyzerFrame):
        bit = self.extract_bit(frame)

        if bit is None:
            return None

        current_time = frame.start_time

        # First bit
        if self.frame_start_time is None:
            self.start_new_frame(frame, bit)
            return None

        # ============================================================
        # Pending early edge 처리
        # ============================================================
        # pending edge가 있다는 것은 직전 edge가 1.6~1.85us로
        # 약간 빠른 edge였다는 뜻이다.
        #
        # 직후 글리치형:
        #   A -> B = 1.7us
        #   B -> C = 0.3us
        #   A -> C = 2.0us
        #
        # 판정:
        #   B는 글리치성 분열 edge로 버림
        #   C를 정상 edge로 채택
        #
        # split-tail 조건이 아니면 pending edge를 정상 edge로 확정한 뒤,
        # 현재 edge를 다시 판단한다.
        # ============================================================

        if (
            self.enable_split_edge_glitch_guard
            and self.pending_edge_frame is not None
        ):
            tail_gap_us = float(
                current_time - self.pending_edge_time
            ) * 1_000_000.0

            merged_gap_us = float(
                current_time - self.last_bit_time
            ) * 1_000_000.0

            if (
                tail_gap_us <= self.split_tail_max_us
                and self.merged_edge_min_us <= merged_gap_us <= self.merged_edge_max_us
            ):
                # pending edge는 버리고 현재 edge를 정상 edge로 채택한다.
                self.ignored_glitch_count += 1
                self.split_edge_merge_count += 1

                self.accept_bit_edge(frame, bit, merged_gap_us)
                self.clear_pending_edge()

                return None

            # 현재 edge가 split-tail이 아니면 pending edge를 정상 edge로 확정한다.
            pending_frame = self.pending_edge_frame
            pending_bit = self.pending_edge_bit
            pending_gap_us = self.pending_edge_gap_us

            self.accept_bit_edge(
                pending_frame,
                pending_bit,
                pending_gap_us,
            )

            self.clear_pending_edge()

            # 이후 현재 edge는 pending 확정 후의 last_bit_time 기준으로 다시 판단한다.

        dt_us = float(current_time - self.last_bit_time) * 1_000_000.0

        # =========================
        # Long gap = frame boundary
        # =========================

        if dt_us >= self.long_gap_detect_threshold_us:
            out = self.finalize_frame(frame, dt_us)

            # Current bit belongs to next frame
            self.start_new_frame(frame, bit)

            return out

        # ============================================================
        # Split edge glitch guard
        # ============================================================

        if self.enable_split_edge_glitch_guard:
            # Case 1. 직전 글리치형
            #
            # A -> B = 0.3us
            # B는 글리치로 보고 버린다.
            # last_bit_time은 갱신하지 않는다.
            #
            # 다음 edge C가 들어오면 A -> C 기준으로 다시 판단한다.
            if dt_us < self.glitch_edge_max_us:
                self.ignored_glitch_count += 1
                return None

            # Case 2. 직후 글리치형
            #
            # A -> B = 1.7us
            # B가 진짜 정상일 수도 있지만,
            # 뒤에 0.3us edge가 붙어서 A -> C = 2.0us가 될 수 있다.
            #
            # 따라서 바로 append하지 않고 pending으로 보류한다.
            if self.early_edge_min_us <= dt_us <= self.early_edge_max_us:
                self.store_pending_edge(frame, bit, dt_us)
                return None

        # =========================
        # Normal bit interval
        # =========================

        self.accept_bit_edge(frame, bit, dt_us)

        # Protection logic
        if len(self.bits) > 128:
            binary_raw = self.bits_to_string(self.bits)

            out = self.make_result_frame(
                frame,
                "FAIL",
                "FRAME_TOO_LONG_NO_LONG_GAP",
                binary_raw,
                "",
                "",
                len(self.bits),
                0.0,
                0.0,
                0.0,
                binary_raw,
                len(self.bits),
            )

            self.reset_frame()
            return out

        return None
