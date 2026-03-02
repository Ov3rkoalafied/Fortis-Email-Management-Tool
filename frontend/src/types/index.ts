export interface EmailTableRow {
  item_id: string
  change_key: string
  subject: string
  sender_name: string
  sender_email: string
  received_time: string
  // Duplicate
  is_duplicate: boolean
  duplicate_group_id: string | null
  duplicate_action: 'keep' | 'delete' | null
  // Numbering
  is_numbered: boolean
  proposed_subject: string | null
  chain_base: string | null
  chain_reason: 'conversation_match' | 'body_match' | 'new_chain' | null
  // User overrides
  include: boolean
  override_subject: boolean
  custom_subject: string | null
  override_abbr: boolean
  custom_abbr: string | null
}

export interface ProjectEmailData {
  project_number: string
  folder_name: string
  rows: EmailTableRow[]
  duplicate_count: number
  numbering_count: number
  error?: string
}

export interface AuthStatus {
  authenticated: boolean
  email?: string
  error?: string
}

export interface ApplyResult {
  success: boolean
  processed: number
  errors: string[]
  undo_id?: string
}

export interface UndoOperation {
  operation_id: string
  type: 'duplicate_deletion' | 'numbering'
  timestamp: string
  project_number: string
  count: number
}
