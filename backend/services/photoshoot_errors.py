"""Domain errors for photoshoot submit (HTTP mapping lives in the router)."""


class PhotoshootError(Exception):
    code = "PHOTOSHOOT_ERROR"
    status_code = 400

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class PhotoshootValidationError(PhotoshootError):
    code = "PHOTOSHOOT_INVALID"
    status_code = 422


class PhotoshootProductNotFoundError(PhotoshootError):
    code = "PRODUCT_LINK_NOT_FOUND"
    status_code = 404


class PhotoshootSourceForbiddenError(PhotoshootError):
    code = "SOURCE_IMAGE_FORBIDDEN"
    status_code = 403


class PhotoshootSourceNotReadyError(PhotoshootValidationError):
    code = "SOURCE_IMAGE_NOT_READY"


class PhotoshootKindMismatchError(PhotoshootValidationError):
    code = "SOURCE_IMAGE_KIND_MISMATCH"


class PhotoshootModelUnavailableError(PhotoshootValidationError):
    code = "MODEL_NOT_AVAILABLE"


class PhotoshootPoseInvalidError(PhotoshootValidationError):
    code = "POSE_SELECTION_INVALID"


class PhotoshootTemplateError(PhotoshootValidationError):
    code = "TEMPLATE_NOT_SELECTABLE"


class PhotoshootOverlayTooLongError(PhotoshootValidationError):
    code = "OVERLAY_TEXT_TOO_LONG"


class PhotoshootVariantUnsupportedError(PhotoshootValidationError):
    code = "VARIANT_NOT_SUPPORTED"


class PhotoshootIdempotencyConflictError(PhotoshootError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409


class PhotoshootNotFoundError(PhotoshootError):
    code = "PHOTOSHOOT_NOT_FOUND"
    status_code = 404


class PhotoshootCredentialMissingError(PhotoshootError):
    code = "PROVIDER_CREDENTIAL_MISSING"
    status_code = 503
