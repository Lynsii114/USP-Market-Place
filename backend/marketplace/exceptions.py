class ApiError(Exception):
    def __init__(self, detail, status=400):
        super().__init__(detail)
        self.detail = detail
        self.status = status

