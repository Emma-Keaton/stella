/**
 * @stella/types - Core entity types
 */

export type ID = string;
export type Timestamp = string;
export type JSONValue =
  | string
  | number
  | boolean
  | null
  | JSONValue[]
  | { [key: string]: JSONValue };

export interface Entity {
  id: ID;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
