// Real Estate Domain Types for OrcaAI Assistant

// Lead Management Types
export interface Lead {
  id: string;
  name: string;
  email: string;
  phone?: string;
  budget: number;
  preferences: PropertyPreferences;
  timeline: string;
  source: LeadSource;
  score: number; // 0-1 lead quality score
  status: LeadStatus;
  createdAt: Date;
  updatedAt: Date;
  lastContact?: Date;
  notes?: string;
  tags: string[];
  assignedAgent?: string;
}

export interface PropertyPreferences {
  propertyTypes: PropertyType[];
  minPrice: number;
  maxPrice: number;
  bedrooms: number;
  bathrooms: number;
  minSquareFeet: number;
  maxSquareFeet: number;
  locations: string[];
  features: string[];
  mustHaves: string[];
  niceToHaves: string[];
}

export type LeadSource = 
  | 'email'
  | 'website'
  | 'referral'
  | 'social_media'
  | 'open_house'
  | 'advertisement'
  | 'other';

export type LeadStatus = 
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'showing_scheduled'
  | 'offer_made'
  | 'under_contract'
  | 'closed'
  | 'lost'
  | 'archived';

// Property Types
export interface Property {
  id: string;
  address: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  squareFeet: number;
  type: PropertyType;
  features: string[];
  mlsId?: string;
  images: string[];
  description: string;
  location: GeoLocation;
  status: PropertyStatus;
  yearBuilt?: number;
  lotSize?: number;
  hoaFees?: number;
  taxes?: number;
  listedDate?: Date;
  agentId?: string;
  virtualTourUrl?: string;
}

export type PropertyType = 
  | 'single_family'
  | 'condo'
  | 'townhouse'
  | 'multi_family'
  | 'land'
  | 'commercial'
  | 'luxury';

export type PropertyStatus = 
  | 'active'
  | 'pending'
  | 'sold'
  | 'off_market'
  | 'coming_soon'
  | 'price_reduced';

export interface GeoLocation {
  address: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  latitude?: number;
  longitude?: number;
  neighborhood?: string;
  schoolDistrict?: string;
}

// Showing and Appointment Types
export interface Showing {
  id: string;
  propertyId: string;
  leadId: string;
  agentId: string;
  scheduledTime: Date;
  duration: number; // minutes
  status: ShowingStatus;
  notes?: string;
  participants: Participant[];
  reminders: Reminder[];
  feedback?: ShowingFeedback;
  createdAt: Date;
  updatedAt: Date;
}

export type ShowingStatus = 
  | 'scheduled'
  | 'confirmed'
  | 'completed'
  | 'cancelled'
  | 'no_show'
  | 'rescheduled';

export interface Participant {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: 'lead' | 'agent' | 'co_agent' | 'other';
  confirmed: boolean;
}

export interface Reminder {
  id: string;
  type: 'email' | 'sms' | 'push' | 'calendar';
  time: Date; // When to send the reminder
  sent: boolean;
  message?: string;
}

export interface ShowingFeedback {
  rating: number; // 1-5 stars
  comments: string;
  interestLevel: 'low' | 'medium' | 'high';
  nextSteps?: string;
  followUpDate?: Date;
}

// Document and Property Packet Types
export interface Document {
  id: string;
  name: string;
  type: DocumentType;
  url: string;
  size: number; // in bytes
  mimeType: string;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  sharedWith: string[];
  tags: string[];
}

export type DocumentType = 
  | 'property_summary'
  | 'disclosure'
  | 'inspection_report'
  | 'appraisal'
  | 'contract'
  | 'cover_letter'
  | 'mls_sheet'
  | 'photos'
  | 'floor_plan'
  | 'other';

export interface PropertyPacket {
  id: string;
  propertyId: string;
  leadId: string;
  documents: Document[];
  shareLink: string;
  createdAt: Date;
  expiresAt?: Date;
  accessed: boolean;
  accessCount: number;
  lastAccessed?: Date;
}

// CRM and Pipeline Types
export interface Pipeline {
  id: string;
  name: string;
  stages: PipelineStage[];
  defaultStage: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface PipelineStage {
  id: string;
  name: string;
  description: string;
  order: number;
  probability: number; // 0-100
  estimatedDays: number;
  requirements: string[];
}

export interface Activity {
  id: string;
  leadId: string;
  type: ActivityType;
  description: string;
  timestamp: Date;
  createdBy: string;
  duration?: number; // in minutes
  outcome?: string;
  nextAction?: string;
  nextActionDate?: Date;
}

export type ActivityType = 
  | 'call'
  | 'email'
  | 'text'
  | 'meeting'
  | 'showing'
  | 'note'
  | 'task'
  | 'other';

// Analytics and Reporting Types
export interface LeadAnalytics {
  totalLeads: number;
  newLeads: number;
  contactedLeads: number;
  qualifiedLeads: number;
  conversionRate: number;
  averageLeadScore: number;
  topSources: LeadSourceCount[];
  averageResponseTime: number; // in hours
}

export interface LeadSourceCount {
  source: LeadSource;
  count: number;
  percentage: number;
}

export interface AgentPerformance {
  agentId: string;
  agentName: string;
  totalLeads: number;
  convertedLeads: number;
  conversionRate: number;
  averageResponseTime: number;
  totalShowings: number;
  completedShowings: number;
  showingConversionRate: number;
  revenueGenerated?: number;
  activitiesCompleted: number;
}

export interface MarketAnalytics {
  averagePrice: number;
  medianPrice: number;
  daysOnMarket: number;
  inventory: number;
  absorptionRate: number;
  pricePerSquareFoot: number;
  marketTrend: 'up' | 'down' | 'stable';
  hotNeighborhoods: string[];
}

// Communication Templates
export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  type: EmailTemplateType;
  variables: string[];
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export type EmailTemplateType = 
  | 'lead_welcome'
  | 'showing_confirmation'
  | 'showing_follow_up'
  | 'property_packet'
  | 'offer_update'
  | 'closing_notification'
  | 'custom';

// Search and Filter Types
export interface PropertySearchCriteria {
  location?: string;
  minPrice?: number;
  maxPrice?: number;
  bedrooms?: number;
  bathrooms?: number;
  propertyTypes?: PropertyType[];
  features?: string[];
  squareFeet?: {
    min: number;
    max: number;
  };
  keywords?: string[];
  status?: PropertyStatus[];
}

export interface LeadSearchCriteria {
  name?: string;
  email?: string;
  phone?: string;
  status?: LeadStatus[];
  source?: LeadSource[];
  score?: {
    min: number;
    max: number;
  };
  assignedAgent?: string;
  tags?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
}

// Configuration and Settings Types
export interface AgentSettings {
  id: string;
  agentId: string;
  workingHours: {
    monday: TimeRange;
    tuesday: TimeRange;
    wednesday: TimeRange;
    thursday: TimeRange;
    friday: TimeRange;
    saturday: TimeRange;
    sunday: TimeRange;
  };
  timezone: string;
  defaultShowingDuration: number;
  bufferTime: number;
  autoReplyEnabled: boolean;
  notificationPreferences: NotificationPreferences;
  emailSignature: string;
}

export interface TimeRange {
  start: string; // "09:00"
  end: string; // "17:00"
  enabled: boolean;
}

export interface NotificationPreferences {
  email: boolean;
  sms: boolean;
  push: boolean;
  newLead: boolean;
  showingScheduled: boolean;
  showingReminder: boolean;
  taskDue: boolean;
  documentShared: boolean;
}

// Utility Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface FilterOptions {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface SearchResult<T> {
  items: T[];
  totalCount: number;
  facets?: Record<string, unknown>;
  suggestions?: string[];
}
