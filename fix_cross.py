# Read the file
with open('static/app.html', 'r') as f:
    lines = f.readlines()

# Find CROSS_PROMO start and end
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'const CROSS_PROMO = {' in line:
        start_idx = i
    if start_idx and i > start_idx and 'async function applyTemplate' in line:
        end_idx = i
        break

new_cross = """        const CROSS_PROMO = {
            onlyfans_support: {
                instagram: [{type: 'Story', time: '10:00'}],
                tiktok: [{type: 'Video', time: '11:00'}],
                twitter: [{type: 'Tweet', time: '09:00'}],
                snapchat: [{type: 'Story', time: '12:00'}],
                reddit: [{type: 'Post', time: '10:00'}],
                onlyfans: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}],
                fansly: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}]
            },
            tiktok_support: {
                instagram: [{type: 'Reel', time: '11:00'}],
                twitter: [{type: 'Tweet', time: '11:30'}],
                onlyfans: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}],
                fansly: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}]
            },
            fansly_support: {
                instagram: [{type: 'Story', time: '10:00'}],
                tiktok: [{type: 'Video', time: '11:00'}],
                onlyfans: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}],
                fansly: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}]
            },
            instagram_support: {
                tiktok: [{type: 'Video', time: '11:00'}],
                twitter: [{type: 'Tweet', time: '11:00'}],
                onlyfans: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}],
                fansly: [{type: 'Post', time: '20:00'}, {type: 'Story', time: '21:00'}]
            }
        };

"""

new_lines = lines[:start_idx] + [new_cross] + lines[end_idx:]

with open('static/app.html', 'w') as f:
    f.writelines(new_lines)

print("✅ Fixed!")
