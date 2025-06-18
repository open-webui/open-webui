// lib/types_db.ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      // TODO: Define your tables here based on Step 2 of the main plan
      // Example:
      // chats: {
      //   Row: {
      //     id: string
      //     user_id: string
      //     title: string | null
      //     created_at: string
      //     updated_at: string
      //     settings_snapshot: Json | null
      //   }
      //   Insert: {
      //     id?: string
      //     user_id: string
      //     title?: string | null
      //     created_at?: string
      //     updated_at?: string
      //     settings_snapshot?: Json | null
      //   }
      //   Update: {
      //     id?: string
      //     user_id?: string
      //     title?: string | null
      //     created_at?: string
      //     updated_at?: string
      //     settings_snapshot?: Json | null
      //   }
      //   Relationships: [
      //     {
      //       foreignKeyName: "chats_user_id_fkey"
      //       columns: ["user_id"]
      //       referencedRelation: "users"
      //       referencedColumns: ["id"]
      //     }
      //   ]
      // }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}
