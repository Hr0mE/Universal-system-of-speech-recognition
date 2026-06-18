"""Stream tags: string constants for pipeline stage I/O declarations.

Plugins may introduce their own tags — any string is valid.
"""

SEGMENTS        = "segments"         # audio segments produced by segmentation
SPEAKER_LABELS  = "speaker_labels"   # diarization completed
LANGUAGE_LABELS = "language_labels"  # language detection completed
TRANSCRIPT      = "transcript"       # ASR completed
