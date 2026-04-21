import { writable } from 'svelte/store';

// Shared chats selection state

// Selected shared chat IDs (persist across pages)
export const selectedChatIds = writable<Set<string>>(new Set());

// Clear all selected IDs
export const clearSelection = () => {
  selectedChatIds.set(new Set());
};

// Toggle a single chat selection
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

// Select all chats on current page
export const selectAllOnPage = (chatIds: string[]) => {
  selectedChatIds.update(set => {
    const newSet = new Set(set);
    chatIds.forEach(id => newSet.add(id));
    return newSet;
  });
};

// Deselect all chats on current page
export const deselectAllOnPage = (chatIds: string[]) => {
  selectedChatIds.update(set => {
    const newSet = new Set(set);
    chatIds.forEach(id => newSet.delete(id));
    return newSet;
  });
};
