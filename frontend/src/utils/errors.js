function normalizeValidationItem(item) {
  if (!item || typeof item !== "object") {
    return String(item || "");
  }

  const location = Array.isArray(item.loc) ? item.loc.join(".") : item.loc;
  const message = item.msg || item.message || JSON.stringify(item);
  return location ? `${location}: ${message}` : message;
}

export function getErrorMessage(error, fallback = "Something went wrong.") {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map(normalizeValidationItem).filter(Boolean);
    return messages.length ? messages.join(" | ") : fallback;
  }

  if (detail && typeof detail === "object") {
    return normalizeValidationItem(detail);
  }

  if (typeof error?.message === "string" && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export function toDisplayText(value, fallback = "Insufficient data") {
  if (value === null || value === undefined) {
    return fallback;
  }

  if (typeof value === "string") {
    return value.trim() || fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    const parts = value.map((item) => toDisplayText(item, "")).filter(Boolean);
    return parts.length ? parts.join(", ") : fallback;
  }

  if (typeof value === "object") {
    if (typeof value.msg === "string") {
      return value.msg;
    }
    return JSON.stringify(value);
  }

  return fallback;
}
