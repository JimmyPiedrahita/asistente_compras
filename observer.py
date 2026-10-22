# PATRÓN 2: OBSERVER (sujeto observable reutilizable)

class SujetoObservable:
    """Mantiene una lista de observadores y los notifica al cambiar."""

    def __init__(self):
        self._observadores = []

    def agregar_observador(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover_observador(self, observador):
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar_observadores(self, mensaje: str = ""):
        for observador in list(self._observadores):
            observador.actualizar(self, mensaje)
