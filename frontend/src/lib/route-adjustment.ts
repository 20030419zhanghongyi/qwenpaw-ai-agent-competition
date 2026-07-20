import type { RouteNode, RouteTemplate } from "@/types";
import type {
  RouteAdjustmentDraft,
  RouteAdjustmentResult,
  RouteNodeChange,
} from "@/types/routes";

function orderedNodes(nodes: RouteNode[]): RouteNode[] {
  return [...nodes].sort((left, right) => left.order - right.order);
}

/**
 * Treat the route visible to the user as the source of truth.
 *
 * The backend currently computes its change lists against the persisted
 * template, which may differ from the already matched or previously adjusted
 * route. Rebuilding the structural diff here prevents stale template nodes
 * from leaking into the preview.
 */
export function buildRouteAdjustmentDraft(
  currentRoute: RouteTemplate,
  result: RouteAdjustmentResult,
): RouteAdjustmentDraft {
  const before = orderedNodes(currentRoute.nodes ?? []);
  const after = orderedNodes(result.route.nodes ?? []);
  const beforeById = new Map(before.map((node) => [node.poi_id, node]));
  const afterById = new Map(after.map((node) => [node.poi_id, node]));

  const addedNodes: RouteNodeChange[] = after
    .filter((node) => !beforeById.has(node.poi_id))
    .map((node) => ({ ...node, new_order: node.order }));
  const removedNodes: RouteNodeChange[] = before
    .filter((node) => !afterById.has(node.poi_id))
    .map((node) => ({ ...node, previous_order: node.order }));

  // Insertion and deletion naturally shift numeric order values. Only report
  // a reorder when the relative order of nodes retained by both routes changed.
  const commonBefore = before.filter((node) => afterById.has(node.poi_id));
  const commonAfter = after.filter((node) => beforeById.has(node.poi_id));
  const beforeCommonIndex = new Map(
    commonBefore.map((node, index) => [node.poi_id, index]),
  );
  const reorderedNodes: RouteNodeChange[] = commonAfter
    .filter(
      (node, index) => beforeCommonIndex.get(node.poi_id) !== index,
    )
    .map((node) => ({
      ...node,
      previous_order: beforeById.get(node.poi_id)?.order,
      new_order: node.order,
    }));

  return {
    ...result,
    added_nodes: addedNodes,
    removed_nodes: removedNodes,
    reordered_nodes: reorderedNodes,
    has_actual_changes:
      addedNodes.length > 0 ||
      removedNodes.length > 0 ||
      reorderedNodes.length > 0,
  };
}
