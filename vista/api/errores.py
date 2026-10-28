class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class SesionNoEncontrada(ApiError):
    def __init__(self):
        super().__init__(401, "Sesión inválida o expirada")


class OperacionNoPermitida(ApiError):
    def __init__(self, operacion: str):
        super().__init__(403, f"Operación no permitida: {operacion}")
