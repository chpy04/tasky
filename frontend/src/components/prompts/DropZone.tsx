import { useDroppable } from "@dnd-kit/core";
import { useRef, useImperativeHandle, forwardRef } from "react";
import styles from "./DropZone.module.css";

export interface DropZoneHandle {
  getY: () => number | null;
}

interface DropZoneProps {
  id: string;
  isNearest: boolean;
  isChainLink?: boolean;
}

const DropZone = forwardRef<DropZoneHandle, DropZoneProps>(function DropZone(
  { id, isNearest, isChainLink },
  ref,
) {
  const divRef = useRef<HTMLDivElement>(null);
  const { setNodeRef, isOver } = useDroppable({ id });

  useImperativeHandle(ref, () => ({
    getY: () => {
      if (!divRef.current) return null;
      const rect = divRef.current.getBoundingClientRect();
      return rect.top + rect.height / 2;
    },
  }));

  const setRefs = (node: HTMLDivElement | null) => {
    (divRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
    setNodeRef(node);
  };

  if (isChainLink && !isNearest) {
    return <div ref={setRefs} className={styles.chainLinkZone} />;
  }

  return (
    <div
      ref={setRefs}
      className={`${styles.zone} ${isNearest ? styles.active : ""} ${isOver ? styles.over : ""}`}
    />
  );
});

export default DropZone;
