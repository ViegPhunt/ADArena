-- Add CHECK action fields
ALTER TABLE teamtasks 
ADD COLUMN IF NOT EXISTS check_status INTEGER DEFAULT -1,
ADD COLUMN IF NOT EXISTS check_message TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS check_private TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS check_attempts INTEGER DEFAULT 0;

-- Add PUT action fields
ALTER TABLE teamtasks 
ADD COLUMN IF NOT EXISTS put_status INTEGER DEFAULT -1,
ADD COLUMN IF NOT EXISTS put_message TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS put_private TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS put_attempts INTEGER DEFAULT 0;

-- Add GET action fields
ALTER TABLE teamtasks 
ADD COLUMN IF NOT EXISTS get_status INTEGER DEFAULT -1,
ADD COLUMN IF NOT EXISTS get_message TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS get_private TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS get_attempts INTEGER DEFAULT 0;

-- Add constraints for action status validation
ALTER TABLE teamtasks 
ADD CONSTRAINT check_status_valid CHECK (check_status IN (-1, 101, 102, 103, 104, 110)),
ADD CONSTRAINT put_status_valid CHECK (put_status IN (-1, 101, 102, 103, 104, 110)),
ADD CONSTRAINT get_status_valid CHECK (get_status IN (-1, 101, 102, 103, 104, 110)),
ADD CONSTRAINT attempts_valid CHECK (check_attempts >= 0 AND put_attempts >= 0 AND get_attempts >= 0);

-- Update existing records: initialize with default values
UPDATE teamtasks SET 
    check_status = -1,
    check_message = '',
    check_private = '',
    check_attempts = 0,
    put_status = -1,
    put_message = '',
    put_private = '',
    put_attempts = 0,
    get_status = -1,
    get_message = '',
    get_private = '',
    get_attempts = 0
WHERE check_status IS NULL;

-- Modify status column to have default
ALTER TABLE teamtasks ALTER COLUMN status SET DEFAULT -1;

-- Comment on new columns
COMMENT ON COLUMN teamtasks.check_status IS 'Status of CHECK action: -1=not run, 101=OK, 110=FAILED';
COMMENT ON COLUMN teamtasks.put_status IS 'Status of PUT action: -1=not run, 101=OK, 110=FAILED';
COMMENT ON COLUMN teamtasks.get_status IS 'Status of GET action: -1=not run, 101=OK, 110=FAILED';
COMMENT ON COLUMN teamtasks.check_attempts IS 'Number of CHECK action attempts (for retry tracking)';
COMMENT ON COLUMN teamtasks.put_attempts IS 'Number of PUT action attempts (for retry tracking)';
COMMENT ON COLUMN teamtasks.get_attempts IS 'Number of GET action attempts (for retry tracking)';

-- Create index for faster queries on action status
CREATE INDEX IF NOT EXISTS idx_teamtasks_check_status ON teamtasks(check_status);
CREATE INDEX IF NOT EXISTS idx_teamtasks_put_status ON teamtasks(put_status);
CREATE INDEX IF NOT EXISTS idx_teamtasks_get_status ON teamtasks(get_status);