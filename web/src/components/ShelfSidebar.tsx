import { useEffect, useState } from "react";
import { createShelf, deleteShelf, getShelves, renameShelf } from "../api/client";
import type { Shelf } from "../types/document";

interface Props {
  activeShelfId: string | null;
  onSelectShelf: (shelfId: string | null) => void;
}

export default function ShelfSidebar({ activeShelfId, onSelectShelf }: Props) {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newNameJa, setNewNameJa] = useState("");
  const [editingShelfId, setEditingShelfId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingNameJa, setEditingNameJa] = useState("");

  const loadShelves = () => {
    getShelves().then(setShelves).catch(console.error);
  };

  useEffect(() => {
    loadShelves();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await createShelf(newName.trim(), newNameJa.trim());
      setNewName("");
      setNewNameJa("");
      setShowCreate(false);
      loadShelves();
    } catch (e) {
      console.error(e);
      alert(`Failed to create shelf: ${e}`);
    }
  };

  const startRename = (shelf: Shelf) => {
    setShowCreate(false);
    setEditingShelfId(shelf.shelf_id);
    setEditingName(shelf.name);
    setEditingNameJa(shelf.name_ja || "");
  };

  const cancelRename = () => {
    setEditingShelfId(null);
    setEditingName("");
    setEditingNameJa("");
  };

  const handleRename = async () => {
    if (!editingShelfId || !editingName.trim()) return;

    const oldShelfId = editingShelfId;
    try {
      const renamed = await renameShelf(
        oldShelfId,
        editingName.trim(),
        editingNameJa.trim(),
      );
      cancelRename();
      if (activeShelfId === oldShelfId) {
        onSelectShelf(renamed.shelf_id);
      }
      loadShelves();
    } catch (e) {
      console.error(e);
      alert(`Failed to rename shelf: ${e}`);
    }
  };

  const handleDelete = async (shelfId: string) => {
    if (!confirm("Delete this shelf? Documents in it will become unsorted.")) return;
    try {
      await deleteShelf(shelfId);
      if (activeShelfId === shelfId) {
        onSelectShelf(null);
      }
      loadShelves();
    } catch (e) {
      console.error(e);
      alert(`Failed to delete shelf: ${e}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleCreate();
    }
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleRename();
    }
    if (e.key === "Escape") {
      cancelRename();
    }
  };

  return (
    <div className="shelf-sidebar">
      <div className="shelf-sidebar-header">
        <span className="shelf-sidebar-title">Shelves</span>
        <button
          className="btn shelf-add-btn"
          onClick={() => setShowCreate((prev) => !prev)}
          title="Create shelf"
        >
          +
        </button>
      </div>

      <div
        className={`shelf-item ${activeShelfId === null ? "active" : ""}`}
        onClick={() => onSelectShelf(null)}
      >
        <span>All</span>
      </div>

      {shelves.map((shelf) => (
        <div key={shelf.shelf_id} className="shelf-row">
          <div
            className={`shelf-item ${activeShelfId === shelf.shelf_id ? "active" : ""}`}
            onClick={() => onSelectShelf(shelf.shelf_id)}
          >
            <span>{shelf.name}</span>
            <div className="shelf-item-right">
              <span className="shelf-count">{shelf.document_count}</span>
              {!shelf.is_virtual && (
                <>
                  <button
                    className="shelf-rename-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      startRename(shelf);
                    }}
                    title="Rename shelf"
                  >
                    ✎
                  </button>
                  <button
                    className="shelf-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(shelf.shelf_id);
                    }}
                    title="Delete shelf"
                  >
                    &times;
                  </button>
                </>
              )}
            </div>
          </div>

          {editingShelfId === shelf.shelf_id && (
            <div className="shelf-inline-form">
              <input
                placeholder="Name"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onKeyDown={handleRenameKeyDown}
                autoFocus
              />
              <input
                placeholder="名前 (Ja)"
                value={editingNameJa}
                onChange={(e) => setEditingNameJa(e.target.value)}
                onKeyDown={handleRenameKeyDown}
              />
              <div className="shelf-inline-actions">
                <button className="btn btn-primary btn-sm" onClick={handleRename}>
                  Save
                </button>
                <button className="btn btn-sm" onClick={cancelRename}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {showCreate && (
        <div className="shelf-create-form">
          <input
            placeholder="Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <input
            placeholder="名前 (Ja)"
            value={newNameJa}
            onChange={(e) => setNewNameJa(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="btn btn-primary btn-sm" onClick={handleCreate}>
            Create
          </button>
        </div>
      )}
    </div>
  );
}
