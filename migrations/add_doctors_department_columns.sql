-- Add new columns to departments table for doctors department settings
ALTER TABLE departments
ADD COLUMN IF NOT EXISTS shift_start_time TIME DEFAULT '08:00:00' NOT NULL,
ADD COLUMN IF NOT EXISTS shift_end_time TIME DEFAULT '15:00:00' NOT NULL,
ADD COLUMN IF NOT EXISTS shift_hours INTEGER DEFAULT 7 NOT NULL,
ADD COLUMN IF NOT EXISTS late_start_time TIME DEFAULT '08:30:00' NOT NULL,
ADD COLUMN IF NOT EXISTS attendance_end_time TIME DEFAULT '11:00:00' NOT NULL,
ADD COLUMN IF NOT EXISTS evening_shift_start_time TIME,
ADD COLUMN IF NOT EXISTS evening_shift_end_time TIME,
ADD COLUMN IF NOT EXISTS evening_shift_hours INTEGER;

-- Add overtime and shift deficit columns to attendance_records table
ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS overtime_hours REAL DEFAULT 0.0 NOT NULL,
ADD COLUMN IF NOT EXISTS shift_deficit_hours REAL DEFAULT 0.0 NOT NULL;
