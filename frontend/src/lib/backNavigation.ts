import type { NavigateFunction } from "react-router-dom";

export function navigateBack(
  navigate: NavigateFunction,
  locationKey: string,
  fallback = "/preferences",
) {
  if (locationKey !== "default" && window.history.length > 1) {
    navigate(-1);
    return;
  }
  navigate(fallback);
}
