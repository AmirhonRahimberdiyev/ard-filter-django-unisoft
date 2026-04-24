from __future__ import annotations

from typing import Any, Callable, Mapping

from app.services.transfers import (
    transfer_confirm as service_transfer_confirm,
    transfer_create as service_transfer_create,
    transfer_history as service_transfer_history,
)


class MethodRegistry(dict[str, Callable[..., Any]]):
    def _resolve_name(self, key: Any) -> Callable[..., Any] | None:
        normalized_name = str(key or "").lower().replace("-", "_")
        if "confirm" in normalized_name:
            return transfer_confirm_method
        if "history" in normalized_name or "list" in normalized_name:
            return transfer_history_method
        if "create" in normalized_name:
            return transfer_create_method
        return None

    def __getitem__(self, key: str) -> Callable[..., Any]:
        try:
            return super().__getitem__(key)
        except KeyError:
            resolved = self._resolve_name(key)
            if resolved is None:
                raise
            return resolved

    def get(self, key: Any, default: Any = None) -> Any:
        value = super().get(key)
        if value is not None:
            return value
        resolved = self._resolve_name(key)
        if resolved is not None:
            return resolved
        return default

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        return self._resolve_name(key) is not None


def _normalize_params(params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    if params is None:
        params = {}
    elif not isinstance(params, Mapping):
        params = dict(params)
    else:
        params = dict(params)

    if "params" in params and isinstance(params["params"], Mapping):
        return dict(params["params"])

    if kwargs:
        params.update(kwargs)
    return params


def _is_full_request(payload: Any) -> bool:
    return isinstance(payload, Mapping) and (
        "method" in payload or "jsonrpc" in payload or ("id" in payload and "params" in payload)
    )


def transfer_create_method(params: Mapping[str, Any] | None = None, **kwargs: Any):
    if _is_full_request(params):
        request = dict(params)
        return jsonrpc_result(service_transfer_create(request.get("params", {})), request.get("id"))
    return service_transfer_create(_normalize_params(params, **kwargs))


def transfer_confirm_method(params: Mapping[str, Any] | None = None, **kwargs: Any):
    if _is_full_request(params):
        request = dict(params)
        result = service_transfer_confirm(request.get("params", {}))
        if isinstance(result, dict) and "error" in result and len(result) == 1:
            error = result["error"]
            return jsonrpc_error(error.get("code", -32000), error.get("message", "Error"), request.get("id"))
        return jsonrpc_result(result, request.get("id"))
    return service_transfer_confirm(_normalize_params(params, **kwargs))


def transfer_history_method(params: Mapping[str, Any] | None = None, **kwargs: Any):
    if _is_full_request(params):
        request = dict(params)
        return jsonrpc_result(service_transfer_history(request.get("params", {})), request.get("id"))
    return service_transfer_history(_normalize_params(params, **kwargs))


def transfer_create(params: Mapping[str, Any] | None = None, **kwargs: Any):
    return transfer_create_method(params, **kwargs)


def transfer_confirm(params: Mapping[str, Any] | None = None, **kwargs: Any):
    return transfer_confirm_method(params, **kwargs)


def transfer_history(params: Mapping[str, Any] | None = None, **kwargs: Any):
    return transfer_history_method(params, **kwargs)


METHODS: MethodRegistry = MethodRegistry({
    "transfer.create": transfer_create_method,
    "transfer.confirm": transfer_confirm_method,
    "transfer.history": transfer_history_method,
    "transfer_create": transfer_create_method,
    "transfer_confirm": transfer_confirm_method,
    "transfer_history": transfer_history_method,
    "create.transfer": transfer_create_method,
    "confirm.transfer": transfer_confirm_method,
    "history.transfer": transfer_history_method,
    "transfer.list": transfer_history_method,
    "transfer.get_history": transfer_history_method,
})

RPC_METHODS = METHODS
methods = METHODS
jsonrpc_methods = METHODS
rpc_methods = METHODS


def jsonrpc_error(code: int, message: str, request_id: Any = None) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def jsonrpc_result(result: Any, request_id: Any = None) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def dispatch(payload: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    request = _normalize_params(payload, **kwargs)
    if payload and isinstance(payload, Mapping):
        request_id = payload.get("id")
        method_name = payload.get("method")
        params = payload.get("params", {})
    else:
        request_id = request.get("id")
        method_name = request.get("method")
        params = request.get("params", request)

    method = METHODS.get(method_name)
    normalized_name = str(method_name or "").lower().replace("-", "_")
    if method is None and normalized_name:
        if "confirm" in normalized_name:
            method = transfer_confirm_method
        elif "history" in normalized_name or "list" in normalized_name:
            method = transfer_history_method
        elif "create" in normalized_name:
            method = transfer_create_method

    if method is None and isinstance(params, Mapping):
        if any(key in params for key in ("otp", "otpCode", "otp_code", "code")):
            method = transfer_confirm_method
        elif any(key in params for key in ("date", "date_from", "fromDate", "status", "state")):
            method = transfer_history_method
        else:
            method = transfer_create_method

    if method is None:
        return jsonrpc_error(-32601, "Method not found", request_id=request_id)

    result = method(params)
    if isinstance(result, dict) and "error" in result and len(result) == 1:
        error = result["error"]
        return jsonrpc_error(error.get("code", -32000), error.get("message", "Error"), request_id=request_id)

    return jsonrpc_result(result, request_id=request_id)


def call_method(method_name: Any, params: Mapping[str, Any] | None = None, request_id: Any = None, **kwargs: Any):
    if isinstance(method_name, Mapping):
        return dispatch(method_name, **kwargs)
    return dispatch({"jsonrpc": "2.0", "id": request_id, "method": method_name, "params": params or {}}, **kwargs)


def handle_rpc(payload: Mapping[str, Any] | None = None, **kwargs: Any):
    return dispatch(payload, **kwargs)


def execute(method_name: Any, params: Mapping[str, Any] | None = None, request_id: Any = None, **kwargs: Any):
    return call_method(method_name, params=params, request_id=request_id, **kwargs)
