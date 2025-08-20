--
-- File generated for Microsoft SQL Server
--
-- Text encoding used: System
--

CREATE DATABASE [openwebui] COLLATE Latin1_General_100_CI_AS_SC_UTF8;
GO

USE [openwebui];
GO



BEGIN TRANSACTION;

-- Table: alembic_version
CREATE TABLE [alembic_version] (
    [version_num] VARCHAR(32) NOT NULL,
    CONSTRAINT [alembic_version_pkc] PRIMARY KEY ([version_num])
);

-- Table: auth
CREATE TABLE [auth] (
    [id] VARCHAR(255) NOT NULL,
    [email] VARCHAR(255) NOT NULL,
    [password] NVARCHAR(MAX) NOT NULL,
    [active] INT NOT NULL
);

-- Table: channel
CREATE TABLE [channel] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX),
    [name] NVARCHAR(MAX),
    [description] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [access_control] NVARCHAR(MAX),
    [created_at] BIGINT,
    [updated_at] BIGINT,
    [type] NVARCHAR(MAX),
    PRIMARY KEY ([id])
);

-- Table: channel_member
CREATE TABLE [channel_member] (
    [id] NVARCHAR(450) NOT NULL,
    [channel_id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(450) NOT NULL,
    [created_at] BIGINT,
    PRIMARY KEY ([id])
);

-- Table: chat
CREATE TABLE [chat] (
    [id] VARCHAR(255) NOT NULL,
    [user_id] VARCHAR(255) NOT NULL,
    [title] NVARCHAR(MAX) NOT NULL,
    [share_id] VARCHAR(255),
    [archived] INT NOT NULL,
    [created_at] DATETIME NOT NULL,
    [updated_at] DATETIME NOT NULL,
    [chat] NVARCHAR(MAX),
    [pinned] BIT,
    [meta] NVARCHAR(MAX) DEFAULT '{}' NOT NULL,
    [folder_id] NVARCHAR(MAX)
);

-- Table: chatidtag
CREATE TABLE [chatidtag] (
    [id] VARCHAR(255) NOT NULL,
    [tag_name] VARCHAR(255) NOT NULL,
    [chat_id] VARCHAR(255) NOT NULL,
    [user_id] VARCHAR(255) NOT NULL,
    [timestamp] INT NOT NULL
);

-- Table: config
CREATE TABLE [config] (
    [id] INT NOT NULL,
    [data] NVARCHAR(MAX) NOT NULL,
    [version] INT NOT NULL,
    [created_at] DATETIME DEFAULT (GETDATE()) NOT NULL,
    [updated_at] DATETIME DEFAULT (GETDATE()),
    PRIMARY KEY ([id])
);

-- Table: document
CREATE TABLE [document] (
    [id] INT NOT NULL PRIMARY KEY,
    [collection_name] VARCHAR(255) NOT NULL,
    [name] VARCHAR(255) NOT NULL,
    [title] NVARCHAR(MAX) NOT NULL,
    [filename] NVARCHAR(MAX) NOT NULL,
    [content] NVARCHAR(MAX),
    [user_id] VARCHAR(255) NOT NULL,
    [timestamp] INT NOT NULL
);

-- Table: feedback
CREATE TABLE [feedback] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX),
    [version] BIGINT,
    [type] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [snapshot] NVARCHAR(MAX),
    [created_at] BIGINT NOT NULL,
    [updated_at] BIGINT NOT NULL,
    PRIMARY KEY ([id])
);

-- Table: file
CREATE TABLE [file] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [filename] NVARCHAR(MAX) NOT NULL,
    [meta] NVARCHAR(MAX),
    [created_at] INT NOT NULL,
    [hash] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [updated_at] BIGINT,
    [path] NVARCHAR(MAX),
    [access_control] NVARCHAR(MAX)
);

-- Table: folder
CREATE TABLE [folder] (
    [id] NVARCHAR(200) NOT NULL,
    [parent_id] NVARCHAR(MAX),
    [user_id] NVARCHAR(200) NOT NULL,
    [name] NVARCHAR(MAX) NOT NULL,
    [items] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [is_expanded] BIT NOT NULL,
    [created_at] BIGINT NOT NULL,
    [updated_at] BIGINT NOT NULL,
    PRIMARY KEY ([id], [user_id])
);

-- Table: function
CREATE TABLE [function] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [name] NVARCHAR(MAX) NOT NULL,
    [type] NVARCHAR(MAX) NOT NULL,
    [content] NVARCHAR(MAX) NOT NULL,
    [meta] NVARCHAR(MAX) NOT NULL,
    [created_at] INT NOT NULL,
    [updated_at] INT NOT NULL,
    [valves] NVARCHAR(MAX),
    [is_active] INT NOT NULL,
    [is_global] INT NOT NULL
);

-- Table: group
CREATE TABLE [group] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX),
    [name] NVARCHAR(MAX),
    [description] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [permissions] NVARCHAR(MAX),
    [user_ids] NVARCHAR(MAX),
    [created_at] BIGINT,
    [updated_at] BIGINT,
    PRIMARY KEY ([id])
);

-- Table: knowledge
CREATE TABLE [knowledge] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [name] NVARCHAR(MAX) NOT NULL,
    [description] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [created_at] BIGINT NOT NULL,
    [updated_at] BIGINT,
    [access_control] NVARCHAR(MAX),
    PRIMARY KEY ([id])
);

-- Table: memory
CREATE TABLE [memory] (
    [id] VARCHAR(255) NOT NULL,
    [user_id] VARCHAR(255) NOT NULL,
    [content] NVARCHAR(MAX) NOT NULL,
    [updated_at] INT NOT NULL,
    [created_at] INT NOT NULL
);

-- Table: message
CREATE TABLE [message] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX),
    [channel_id] NVARCHAR(450),
    [content] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [created_at] BIGINT,
    [updated_at] BIGINT,
    [parent_id] NVARCHAR(MAX),
    PRIMARY KEY ([id])
);

-- Table: message_reaction
CREATE TABLE [message_reaction] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [message_id] NVARCHAR(450) NOT NULL,
    [name] NVARCHAR(MAX) NOT NULL,
    [created_at] BIGINT,
    PRIMARY KEY ([id])
);

-- Table: migratehistory
CREATE TABLE [migratehistory] (
    [id] INT NOT NULL PRIMARY KEY,
    [name] VARCHAR(255) NOT NULL,
    [migrated_at] DATETIME NOT NULL
);

-- Table: model
CREATE TABLE [model] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [base_model_id] NVARCHAR(MAX),
    [name] NVARCHAR(MAX) NOT NULL,
    [meta] NVARCHAR(MAX) NOT NULL,
    [params] NVARCHAR(MAX) NOT NULL,
    [created_at] INT NOT NULL,
    [updated_at] INT NOT NULL,
    [access_control] NVARCHAR(MAX),
    [is_active] BIT DEFAULT (1) NOT NULL
);

-- Table: note
CREATE TABLE [note] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX),
    [title] NVARCHAR(MAX),
    [data] NVARCHAR(MAX),
    [meta] NVARCHAR(MAX),
    [access_control] NVARCHAR(MAX),
    [created_at] BIGINT,
    [updated_at] BIGINT,
    PRIMARY KEY ([id])
);

-- Table: prompt
CREATE TABLE [prompt] (
    [id] INT NOT NULL PRIMARY KEY,
    [command] VARCHAR(255) NOT NULL,
    [user_id] VARCHAR(255) NOT NULL,
    [title] NVARCHAR(MAX) NOT NULL,
    [content] NVARCHAR(MAX) NOT NULL,
    [timestamp] INT NOT NULL,
    [access_control] NVARCHAR(MAX)
);

-- Table: tag
CREATE TABLE [tag] (
    [id] VARCHAR(255) NOT NULL,
    [name] VARCHAR(255) NOT NULL,
    [user_id] VARCHAR(255) NOT NULL,
    [meta] NVARCHAR(MAX),
    CONSTRAINT [pk_id_user_id] PRIMARY KEY ([id], [user_id])
);

-- Table: tool
CREATE TABLE [tool] (
    [id] NVARCHAR(450) NOT NULL,
    [user_id] NVARCHAR(MAX) NOT NULL,
    [name] NVARCHAR(MAX) NOT NULL,
    [content] NVARCHAR(MAX) NOT NULL,
    [specs] NVARCHAR(MAX) NOT NULL,
    [meta] NVARCHAR(MAX) NOT NULL,
    [created_at] INT NOT NULL,
    [updated_at] INT NOT NULL,
    [valves] NVARCHAR(MAX),
    [access_control] NVARCHAR(MAX)
);

-- Table: user
CREATE TABLE [user] (
    [id] VARCHAR(255) NOT NULL,
    [name] VARCHAR(255) NOT NULL,
    [email] VARCHAR(255) NOT NULL,
    [role] VARCHAR(255) NOT NULL,
    [profile_image_url] NVARCHAR(MAX) NOT NULL,
    [api_key] VARCHAR(255),
    [created_at] INT NOT NULL,
    [updated_at] INT NOT NULL,
    [last_active_at] INT NOT NULL,
    [settings] NVARCHAR(MAX),
    [info] NVARCHAR(MAX),
    [oauth_sub] VARCHAR(255)
);

-- Index: auth_id
CREATE UNIQUE INDEX [auth_id] ON [auth] ([id]);

-- Index: chat_id
CREATE UNIQUE INDEX [chat_id] ON [chat] ([id]);

-- Index: chat_share_id
CREATE UNIQUE INDEX [chat_share_id] ON [chat] ([share_id]) WHERE [share_id] IS NOT NULL;

-- Index: chatidtag_id
CREATE UNIQUE INDEX [chatidtag_id] ON [chatidtag] ([id]);

-- Index: document_collection_name
CREATE UNIQUE INDEX [document_collection_name] ON [document] ([collection_name]);

-- Index: document_name
CREATE UNIQUE INDEX [document_name] ON [document] ([name]);

-- Index: file_id
CREATE UNIQUE INDEX [file_id] ON [file] ([id]);

-- Index: function_id
CREATE UNIQUE INDEX [function_id] ON [function] ([id]);

-- Index: memory_id
CREATE UNIQUE INDEX [memory_id] ON [memory] ([id]);

-- Index: model_id
CREATE UNIQUE INDEX [model_id] ON [model] ([id]);

-- Index: prompt_command
CREATE UNIQUE INDEX [prompt_command] ON [prompt] ([command]);

-- Index: tool_id
CREATE UNIQUE INDEX [tool_id] ON [tool] ([id]);

-- Index: user_api_key
CREATE UNIQUE INDEX [user_api_key] ON [user] ([api_key]) WHERE [api_key] IS NOT NULL;

-- Index: user_id
CREATE UNIQUE INDEX [user_id] ON [user] ([id]);

-- Index: user_oauth_sub
CREATE UNIQUE INDEX [user_oauth_sub] ON [user] ([oauth_sub]) WHERE [oauth_sub] IS NOT NULL;

COMMIT TRANSACTION;
GO

-- Grant permissions to the 'app' user
USE [openwebui];
GO
CREATE USER [app] FOR LOGIN [app];
GO
ALTER ROLE [db_datareader] ADD MEMBER [app];
GO
ALTER ROLE [db_datawriter] ADD MEMBER [app];
GO
