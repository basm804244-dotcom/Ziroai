-- Default data seeds

-- Insert default admin user (password: admin123)
INSERT INTO users (id, email, username, full_name, password_hash, role, plan, is_verified)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@aether.ai',
    'admin',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6', -- bcrypt hash of 'admin123'
    'admin',
    'enterprise',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Insert default models
-- Models are managed by the model service, no DB seed needed
