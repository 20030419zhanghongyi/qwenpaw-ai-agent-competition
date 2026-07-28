import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

export interface PointerDragState {
  id: string;
  x: number;
  y: number;
  grabX: number;
  grabY: number;
  width: number;
  height: number;
}

interface PointerDragOptions {
  disabled?: boolean;
  onMove?: (id: string, x: number, y: number) => void;
  onEnd?: (id: string, x: number, y: number) => void;
}

interface PendingDrag extends PointerDragState {
  pointerId: number;
  startX: number;
  startY: number;
  pointerType: string;
}

/**
 * Pointer Events based drag primitive.
 *
 * Unlike native HTML drag-and-drop this works on iOS Safari. Touch/pen input
 * activates after a short hold, while moving deliberately also starts the drag
 * immediately. Callers render their own fixed-position preview from `drag`.
 */
export function usePointerDrag({
  disabled = false,
  onMove,
  onEnd,
}: PointerDragOptions) {
  const [drag, setDrag] = useState<PointerDragState | null>(null);
  const pendingRef = useRef<PendingDrag | null>(null);
  const activeRef = useRef<PointerDragState | null>(null);
  const timerRef = useRef<number | null>(null);
  const onMoveRef = useRef(onMove);
  const onEndRef = useRef(onEnd);

  useEffect(() => {
    onMoveRef.current = onMove;
    onEndRef.current = onEnd;
  }, [onEnd, onMove]);

  useEffect(
    () => () => {
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    },
    [],
  );

  const clearTimer = () => {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const activate = () => {
    const pending = pendingRef.current;
    if (!pending || activeRef.current) return;
    const next: PointerDragState = {
      id: pending.id,
      x: pending.x,
      y: pending.y,
      grabX: pending.grabX,
      grabY: pending.grabY,
      width: pending.width,
      height: pending.height,
    };
    activeRef.current = next;
    setDrag(next);
    onMoveRef.current?.(next.id, next.x, next.y);
  };

  const finish = (cancelled = false) => {
    clearTimer();
    const active = activeRef.current;
    if (active && !cancelled) {
      onEndRef.current?.(active.id, active.x, active.y);
    }
    pendingRef.current = null;
    activeRef.current = null;
    setDrag(null);
  };

  const handleProps = (id: string) => ({
    onPointerDown: (event: ReactPointerEvent<HTMLElement>) => {
      if (disabled || event.button !== 0) return;
      const preview =
        event.currentTarget.closest<HTMLElement>("[data-drag-preview]") ??
        event.currentTarget;
      const rect = preview.getBoundingClientRect();
      const pending: PendingDrag = {
        id,
        pointerId: event.pointerId,
        pointerType: event.pointerType,
        startX: event.clientX,
        startY: event.clientY,
        x: event.clientX,
        y: event.clientY,
        grabX: event.clientX - rect.left,
        grabY: event.clientY - rect.top,
        width: rect.width,
        height: rect.height,
      };
      pendingRef.current = pending;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      if (event.pointerType === "mouse") {
        activate();
      } else {
        timerRef.current = window.setTimeout(activate, 180);
      }
    },
    onPointerMove: (event: ReactPointerEvent<HTMLElement>) => {
      const pending = pendingRef.current;
      if (!pending || pending.pointerId !== event.pointerId) return;
      pending.x = event.clientX;
      pending.y = event.clientY;
      const distance = Math.hypot(
        event.clientX - pending.startX,
        event.clientY - pending.startY,
      );
      if (!activeRef.current && distance > 8) {
        clearTimer();
        activate();
      }
      const active = activeRef.current;
      if (!active) return;
      event.preventDefault();
      const next = { ...active, x: event.clientX, y: event.clientY };
      activeRef.current = next;
      setDrag(next);
      onMoveRef.current?.(next.id, next.x, next.y);

      const edge = 72;
      if (event.clientY < edge) window.scrollBy(0, -10);
      if (event.clientY > window.innerHeight - edge) window.scrollBy(0, 10);
    },
    onPointerUp: (event: ReactPointerEvent<HTMLElement>) => {
      if (pendingRef.current?.pointerId === event.pointerId) finish();
    },
    onPointerCancel: (event: ReactPointerEvent<HTMLElement>) => {
      if (pendingRef.current?.pointerId === event.pointerId) finish(true);
    },
    onLostPointerCapture: () => {
      if (pendingRef.current) finish();
    },
  });

  return { drag, handleProps };
}
