import unittest
from unittest.mock import patch

import pandas as pd

from src.detect import (
    _align_reference_words,
    _merge_records_by_type,
    _silence_intervals,
    detect_anomalies,
)
from src.explain import compute_rubric_scores, generate_causal_explanation


class DetectionAlignmentTests(unittest.TestCase):
    def test_alignment_uses_matching_tokens_with_insertions(self):
        indices, exact = _align_reference_words(
            ["I", "really", "like", "apples!"],
            ["i", "like", "fresh", "apples"],
        )

        self.assertEqual(indices.tolist(), [0, 2, 2, 3])
        self.assertEqual(exact.tolist(), [True, True, False, True])

    def test_merging_is_per_flaw_and_does_not_bridge_large_gaps(self):
        records = [
            {"flaw_type": "rushed_delivery", "start": 1.0, "end": 2.0, "sigma_dev": 0.2, "word": "a"},
            {"flaw_type": "volume_instability", "start": 1.5, "end": 1.8, "sigma_dev": 2.0, "word": "b"},
            {"flaw_type": "rushed_delivery", "start": 2.0, "end": 3.0, "sigma_dev": 0.3, "word": "c"},
            {"flaw_type": "rushed_delivery", "start": 5.0, "end": 6.0, "sigma_dev": 0.4, "word": "d"},
        ]

        regions = _merge_records_by_type(records, merge_gap_sec=0.2)

        rush_regions = [region for region in regions if region["flaw_type"] == "rushed_delivery"]
        self.assertEqual(len(rush_regions), 2)
        self.assertEqual((rush_regions[0]["t_start"], rush_regions[0]["t_end"]), (1.0, 3.0))
        self.assertEqual(rush_regions[0]["words"], ["a", "c"])
        self.assertEqual(rush_regions[1]["t_start"], 5.0)
        self.assertEqual(len([region for region in regions if region["flaw_type"] == "volume_instability"]), 1)

    def test_silence_intervals_use_minimum_duration(self):
        times = [index * 0.1 for index in range(20)]
        rms = [0.1] * 5 + [0.0] * 8 + [0.1] * 7
        with patch("src.detect.compute_rms_energy", return_value=(times, rms)):
            intervals = _silence_intervals("unused.wav", minimum_duration=0.5)

        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 0.45)
        self.assertAlmostEqual(intervals[0][1], 1.25)

    def test_identical_paths_are_analyzed_instead_of_short_circuited(self):
        features = pd.DataFrame(
            {
                "word": ["one", "two"],
                "start": [0.0, 0.5],
                "end": [0.3, 0.8],
                "pause_before": [0.0, 0.2],
                "speech_rate": [2.0, 2.0],
                "f0_median_hz": [120.0, 125.0],
                "f0_hz_zscore": [-0.5, 0.5],
                "rms_energy_zscore": [0.0, 0.0],
            }
        )
        with (
            patch("src.detect.extract_features_per_word", return_value=features) as extract,
            patch("src.detect._silence_intervals", return_value=[]),
        ):
            regions = detect_anomalies("same.wav", "same.wav")

        self.assertEqual(regions, [])
        self.assertEqual(extract.call_count, 2)

    def test_rushed_delivery_score_decays_smoothly_with_severity(self):
        scores = [
            compute_rubric_scores(
                [
                    {
                        "flaw_type": "rushed_delivery",
                        "t_start": 25.0,
                        "t_end": 31.0,
                        "max_sigma": severity,
                    }
                ],
                total_duration_sec=62.0,
            )["pacing_score"]
            for severity in (0.25, 0.50, 0.85)
        ]

        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], scores[2])
        self.assertTrue(7.0 <= scores[0] <= 8.0)
        self.assertTrue(5.0 <= scores[1] <= 7.0)
        self.assertTrue(4.0 <= scores[2] <= 5.0)


    def test_causal_explanations_contain_mathematical_metrics_and_coaching(self):
        flaw_cases = [
            ("rushed_delivery", "Syllabic Acceleration", "Coaching"),
            ("errant_pause", "Errant Pause", "Coaching"),
            ("monotone_pitch", "Monotone Pitch", "Coaching"),
            ("volume_instability", "Dynamic Volume Instability", "Coaching"),
            ("vocal_clarity_drift", "Vocal Clarity / Timbre Drift", "Coaching"),
        ]
        for flaw, expected_keyword, expected_advice in flaw_cases:
            region = {
                "flaw_type": flaw,
                "t_start": 12.0,
                "t_end": 15.5,
                "max_sigma": 2.4,
                "words": ["we", "shall", "prevail"],
                "details": [{
                    "ref_rate": 2.5, "tgt_rate": 4.0, "rate_ratio": 1.6,
                    "pause_dur": 2.8, "silence_delta": 2.1, "ref_pause": 0.4,
                    "ref_pitch_var": 1.2, "tgt_pitch_var": 0.3, "collapse_pct": 75.0,
                    "rms_delta": 2.2, "tgt_rms_z": -1.8, "ref_rms_z": 0.4,
                    "clarity_drift": 0.45
                }]
            }
            text = generate_causal_explanation(region)
            self.assertIn(expected_keyword, text)
            self.assertIn(expected_advice, text)
            self.assertIn("12.00s", text)
            self.assertIn("15.50s", text)


    def test_cross_speaker_normalization_male_vs_female_pitch(self):
        # Female reference (median 210 Hz) vs Male participant (median 120 Hz)
        # Both express normal natural prosodic inflection (varying by +/- 15%)
        words = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
        n = len(words)
        starts = [i * 0.5 for i in range(n)]
        ends = [(i + 1) * 0.5 for i in range(n)]

        ref_features = pd.DataFrame({
            "word": words,
            "start": starts,
            "end": ends,
            "pause_before": [0.0] * n,
            "speech_rate": [2.0] * n,
            "f0_median_hz": [200.0, 220.0, 205.0, 225.0, 210.0, 230.0, 205.0, 215.0],
            "f0_hz_zscore": [0.0] * n,
            "rms_energy_zscore": [0.0] * n,
        })
        male_features = pd.DataFrame({
            "word": words,
            "start": starts,
            "end": ends,
            "pause_before": [0.0] * n,
            "speech_rate": [2.0] * n,
            "f0_median_hz": [115.0, 126.0, 117.0, 128.0, 120.0, 131.0, 117.0, 123.0],
            "f0_hz_zscore": [0.0] * n,
            "rms_energy_zscore": [0.0] * n,
        })

        with (
            patch("src.detect.extract_features_per_word", side_effect=[ref_features, male_features]),
            patch("src.detect._silence_intervals", return_value=[]),
        ):
            regions = detect_anomalies("ref_female.wav", "part_male.wav")

        # Because both speakers have normal relative inflection around their respective medians,
        # neither monotone pitch nor pitch disparity false alarms should be triggered.
        pitch_regions = [r for r in regions if r["flaw_type"] == "monotone_pitch"]
        self.assertEqual(pitch_regions, [])


if __name__ == "__main__":
    unittest.main()
