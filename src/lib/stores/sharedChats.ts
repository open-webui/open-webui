import { writable } from 'svelte/store';

// ============ 成员C 新增：共享聊天状态管理 ============

// 选中的共享聊天ID集合（跨分页保持）
export const selectedChatIds = writable<Set<string>>(new Set());

// 清空所有选中
export const clearSelection = () => {
  selectedChatIds.set(new Set());
};

// 切换单个聊天的选中状态
export const toggleSelectChat = (chatId: string) => {
  selectedChatIds.update(set => {
    const newSet = new Set(set);
    if (newSet.has(chatId)) {
      newSet.delete(chatId);
    } else {
      newSet.add(chatId);
    }
    return newSet;
  });
};

// 全选当前页的所有聊天
export const selectAllOnPage = (chatIds: string[]) => {
  selectedChatIds.update(set => {
    const newSet = new Set(set);
    chatIds.forEach(id => newSet.add(id));
    return newSet;
  });
};

// 取消全选当前页的所有聊天
export const deselectAllOnPage = (chatIds: string[]) => {
  selectedChatIds.update(set => {
    const newSet = new Set(set);
    chatIds.forEach(id => newSet.delete(id));
    return newSet;
  });
};
