/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect } from "react";
import { clsx } from "clsx";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import {
  Bold,
  Heading2,
  Italic,
  List,
  ListOrdered,
  Redo2,
  Table2,
  Trash2,
  Undo2,
} from "lucide-react";

export interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  readOnly?: boolean;
  placeholder?: string;
}

interface ToolbarBtnProps {
  active?: boolean;
  disabled?: boolean;
  title: string;
  onClick: () => void;
  children: React.ReactNode;
}

const ToolbarButton: React.FC<ToolbarBtnProps> = ({
  active = false,
  disabled = false,
  title,
  onClick,
  children,
}) => (
  <button
    type="button"
    title={title}
    aria-label={title}
    disabled={disabled}
    onClick={onClick}
    className={clsx(
      "inline-flex h-8 w-8 items-center justify-center rounded-mm-tag transition-colors disabled:opacity-40",
      active
        ? "bg-mm-blue-light/60 text-mm-blue-deep"
        : "text-mm-text-secondary hover:bg-mm-divider hover:text-mm-heading"
    )}
  >
    {children}
  </button>
);

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  readOnly = false,
}) => {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: value || "",
    editable: !readOnly,
    onUpdate: ({ editor: instance }) => {
      onChange(instance.getHTML());
    },
  });

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!readOnly);
  }, [editor, readOnly]);

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    if (value !== current) {
      editor.commands.setContent(value || "", false);
    }
  }, [editor, value]);

  if (!editor) {
    return (
      <div className="min-h-[220px] rounded-mm-panel border border-mm-border bg-mm-bg p-4 font-mm-ui text-sm text-mm-text-muted">
        Đang khởi tạo trình soạn thảo...
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-mm-panel border border-mm-border bg-mm-bg">
      {!readOnly && (
        <div className="flex flex-wrap items-center gap-1 border-b border-mm-divider bg-mm-bg px-3 py-2">
          <ToolbarButton
            title="In đậm"
            active={editor.isActive("bold")}
            onClick={() => editor.chain().focus().toggleBold().run()}
          >
            <Bold className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            title="In nghiêng"
            active={editor.isActive("italic")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
          >
            <Italic className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            title="Tiêu đề mục"
            active={editor.isActive("heading", { level: 2 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          >
            <Heading2 className="h-4 w-4" />
          </ToolbarButton>

          <span className="mx-1 h-5 w-px bg-mm-border" />

          <ToolbarButton
            title="Danh sách gạch đầu dòng"
            active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
          >
            <List className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            title="Danh sách đánh số"
            active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
          >
            <ListOrdered className="h-4 w-4" />
          </ToolbarButton>

          <span className="mx-1 h-5 w-px bg-mm-border" />

          <ToolbarButton
            title="Chèn bảng (3x3)"
            active={editor.isActive("table")}
            onClick={() =>
              editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
            }
          >
            <Table2 className="h-4 w-4" />
          </ToolbarButton>
          {editor.isActive("table") && (
            <ToolbarButton
              title="Xóa bảng"
              onClick={() => editor.chain().focus().deleteTable().run()}
            >
              <Trash2 className="h-4 w-4 text-mm-danger" />
            </ToolbarButton>
          )}

          <span className="mx-1 h-5 w-px bg-mm-border" />

          <ToolbarButton
            title="Hoàn tác"
            disabled={!editor.can().undo()}
            onClick={() => editor.chain().focus().undo().run()}
          >
            <Undo2 className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            title="Làm lại"
            disabled={!editor.can().redo()}
            onClick={() => editor.chain().focus().redo().run()}
          >
            <Redo2 className="h-4 w-4" />
          </ToolbarButton>
        </div>
      )}

      <div className="mm-editor-content">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
};
