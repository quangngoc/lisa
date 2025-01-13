class TokenLimitError(Exception):
    def __init__(self, message: str, prompt_tokens_count: int, exceeded_tokens_count: int):
        super().__init__(message)
        self.prompt_tokens_count = prompt_tokens_count
        self.exceeded_tokens_count = exceeded_tokens_count
