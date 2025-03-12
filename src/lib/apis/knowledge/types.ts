// Bare minimum types for knowledge from reverse engineering

export type UserId = string;
export type GroupId = string;
export type KnowledgeId = string;
export type KnowledgeFileId = string;

export type KnowledgeFileMetadata = {
  collection_name: string;
  content_type: string;
  name: string;
  size: number;
};

export type KnowledgeFile = {
  created_at: number;
  data: any;
  filename: string;
  hash: string;
  id: KnowledgeId;
  meta: KnowledgeFileMetadata;
  updated_at: number;
  user_id: UserId;
};

export type AccessControl = {
  read: {
    group_ids: GroupId[];
  };
  write: {
    group_ids: GroupId[];
  };
};

export type KnowledgeData = {
  file_ids: KnowledgeFileId[];
};

export type Knowledge = {
  id: KnowledgeId;
  user_id: UserId;
  name: string;
  description: string;
  data: KnowledgeData | null;
  // meta omitted because was always null
  access_control: AccessControl;
  created_at: number;
  updated_at: number;
  files: KnowledgeFile[] | null;
};
