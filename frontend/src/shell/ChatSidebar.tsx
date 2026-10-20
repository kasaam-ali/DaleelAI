/** Middle of the sidebar inside Ask Daleel: Tools icon row, New chat, Search, history (handoff-pr18-nav.md §4). */

import type { ChatSummary } from "../api/chat"
import HistoryList from "../features/chat/HistoryList"
import type { CopyKey } from "../i18n"
import NavLink from "./NavLink"
import Icon from "./icons"
import { TOOLS, type ToolId } from "./nav"

type Copy = (key: CopyKey) => string

export default function ChatSidebar({
  chats,
  activeChatId,
  copy,
  onTool,
  onNewChat,
  onSearch,
  onSelectChat,
  onRename,
  onDelete,
  onToast,
}: {
  chats: ChatSummary[]
  activeChatId: string | null
  copy: Copy
  onTool: (id: ToolId) => void
  onNewChat: () => void
  onSearch: () => void
  onSelectChat: (chatId: string) => void
  onRename: (chatId: string, title: string) => Promise<void>
  onDelete: (chatId: string) => Promise<void>
  onToast: (text: string) => void
}) {
  return (
    <>
      <nav aria-label={copy("navTools")} className="tool-row" data-tool-row>
        <p className="nav-label">{copy("navTools")}</p>
        <div className="tr-icons">
          {TOOLS.filter((item) => item.id !== "ask").map((item) => (
            <NavLink
              key={item.id}
              href={item.href}
              title={copy(item.label)}
              ariaLabel={copy(item.label)}
              className="tr-btn"
              onGo={() => onTool(item.id)}
            >
              <Icon name={item.icon} size="sm" />
            </NavLink>
          ))}
        </div>
      </nav>
      <button type="button" data-new-chat title={copy("newChat")} className="newchat" onClick={onNewChat}>
        <Icon name="plus" />
        <span className="lbl">{copy("newChat")}</span>
      </button>
      <button type="button" data-search-chats title={copy("searchChats")} className="searchbox" onClick={onSearch}>
        <Icon name="search" size="sm" />
        <span className="lbl">{copy("searchChats")}</span>
        <kbd className="lbl">Ctrl K</kbd>
      </button>
      <div className="recents">
        <HistoryList
          chats={chats}
          activeId={activeChatId}
          copy={copy}
          heading={copy("recentsLabel")}
          onSelect={onSelectChat}
          onRename={onRename}
          onDelete={onDelete}
          onOpenNew={onNewChat}
          onToast={onToast}
        />
      </div>
    </>
  )
}
