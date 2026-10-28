export interface Message {
  id: string;
  role: 'user' | 'assistant';
  contenu: string;
  timestamp: number;
  data?: any; // <-- AJOUTE CETTE LIGNE ICI
}

export interface Discussion {
  id: string;
  titre: string;
  date: number; // timestamp
  messages: Message[];
}

const STORAGE_KEY = 'vermeg_discussions';

export const chargerDiscussions = (): Discussion[] => {
  const data = localStorage.getItem(STORAGE_KEY);
  return data ? JSON.parse(data) : [];
};

export const sauvegarderDiscussions = (discussions: Discussion[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(discussions));
};