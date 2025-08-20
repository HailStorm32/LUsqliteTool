class RepositoryError(Exception):
    """Base class for repository-layer errors."""

class NotFoundError(RepositoryError):
    """Requested row/resource was not found."""
    def __init__(self, message: str, *, table: str | None = None, column: str | None = None, value: any = None):
        super().__init__(message)
        self.table = table
        self.value = value
        self.column = column

class DataIntegrityError(RepositoryError):
    """DB content is inconsistent (ie duplicates)."""
    def __init__(self, message: str, *, table: str | None = None, column: str | None = None, value: any = None,
                 dup_count: int | None = None):
        super().__init__(message)
        self.table = table
        self.column = column
        self.value = value
        self.dup_count = dup_count

class SaveError(RepositoryError):
    """Failed to persist changes."""
    def __init__(self, message: str, *, table: str | None = None, column: str | None = None, value: any = None,
                 cause: Exception | None = None):
        super().__init__(message)
        self.table = table
        self.column = column
        self.value = value
        self.__cause__ = cause  # preserve original exception via exception chaining