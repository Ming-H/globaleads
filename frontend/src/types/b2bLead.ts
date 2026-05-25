export type B2BLeadStatus = 'uncontacted' | 'contacted' | 'replied' | 'invalid';

export interface B2BLead {
  id: number;
  task_id: number;
  company_name: string;
  company_website: string;
  company_size: string;
  company_address: string;
  region: string;
  industry: string;
  contact_name: string;
  contact_title: string;
  contact_email: string;
  contact_phone: string;
  contact_twitter: string;
  contact_linkedin: string;
  contact_facebook: string;
  data_source: string;
  status: B2BLeadStatus;
  created_at: string;
}
