// Placeholder for basic types

export type User = {
  id: string;
  email: string;
  name?: string;
};

export type Message = {
  id: string;
  text: string;
  userId: string;
  timestamp: Date;
};
