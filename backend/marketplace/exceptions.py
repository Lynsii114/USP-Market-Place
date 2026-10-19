class ApiError(Exception):
    def __init__(self, detail, status=400, code=None):
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.code = code

