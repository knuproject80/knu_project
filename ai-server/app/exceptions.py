class ModelNotReadyError(Exception):
    """OpenAI client가 아직 초기화되지 않았을 때 발생한다."""


class ModelResponseError(Exception):
    """모델 호출 또는 모델 응답 파싱 과정에서 발생한다."""
