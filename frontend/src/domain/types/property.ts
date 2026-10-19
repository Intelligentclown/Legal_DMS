/** Property representation returned by the existing tenant-scoped Property API. */
export interface PropertyOwner {
  party_id: string | null;
  legacy_client_id: string | null;
  ownership_share: string | null;
  ownership_type: string;
  from_date: string;
  to_date: string | null;
}

export interface Property {
  id: string;
  property_type: string;
  survey_number: string;
  sub_division_number: string | null;
  area_value: string | null;
  area_unit: string | null;
  address_id: string | null;
  village_id: string | null;
  registration_number: string | null;
  owners: PropertyOwner[];
}
