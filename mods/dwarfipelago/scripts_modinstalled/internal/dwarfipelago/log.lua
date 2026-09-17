--@ module = true
-- Lightweight logging for Dwarfipelago.
--
-- Writes timestamped, levelled lines to a log file AND mirrors them to the
-- DFHack console (errors/warnings via printerr so they stand out). The log
-- file lives next to the DF executable so it is easy to find and attach to
-- bug reports:
--     <Dwarf Fortress>/dwarfipelago.log
--
-- Usage:
--     local log = reqscript("internal/dwarfipelago/log")
--     log.info("started")
--     log.warn("something odd")
--     log.error("spawn failed: " .. tostring(err))

local M = {}

-- Resolve the log path once. dfhack.getDFPath() returns the DF root dir.
local function resolve_path()
    local ok, base = pcall(dfhack.getDFPath)
    if ok and base and base ~= "" then
        return base .. "/dwarfipelago.log"
    end
    -- Fallback: current working directory.
    return "dwarfipelago.log"
end

local LOG_PATH = resolve_path()

-- Cap the log so it can't grow without bound across long playthroughs.
local MAX_BYTES = 1024 * 1024  -- 1 MB

local function maybe_rotate()
    local f = io.open(LOG_PATH, "r")
    if not f then return end
    local size = f:seek("end")
    f:close()
    if size and size > MAX_BYTES then
        -- Keep one previous log; overwrite any older one.
        os.remove(LOG_PATH .. ".old")
        os.rename(LOG_PATH, LOG_PATH .. ".old")
    end
end

local function write_line(level, msg)
    local line = ("[%s] [%s] %s"):format(
        os.date("%Y-%m-%d %H:%M:%S"), level, tostring(msg))
    local ok, f = pcall(io.open, LOG_PATH, "a")
    if ok and f then
        f:write(line .. "\n")
        f:close()
    end
    return line
end

function M.path()
    return LOG_PATH
end

function M.info(msg)
    maybe_rotate()
    write_line("INFO", msg)
    print("[Dwarfipelago] " .. tostring(msg))
end

function M.warn(msg)
    maybe_rotate()
    write_line("WARN", msg)
    dfhack.printerr("[Dwarfipelago] WARN: " .. tostring(msg))
end

-- Bracket a risky operation: "> name" before, "< name" after. A hard DF crash
-- leaves no Lua traceback, so a dangling ">" is what pins down where it died.
-- Lines are flushed on write. Use for rare bulk work only, never per poll tick.
function M.scope(name, fn, ...)
    maybe_rotate()
    write_line("SCOPE", "> " .. name)
    local res = table.pack(pcall(fn, ...))
    if res[1] then
        write_line("SCOPE", "< " .. name)
        return table.unpack(res, 2, res.n)
    end
    M.error(("%s raised: %s"):format(name, tostring(res[2])))
    return nil
end

-- One startup block describing the environment, so a bug report is
-- self-describing. `facts` is an ordered list of {label, value} pairs.
function M.session(facts)
    maybe_rotate()
    write_line("INFO", "---- session ----")
    for _, kv in ipairs(facts) do
        write_line("INFO", ("  %-22s %s"):format(kv[1], tostring(kv[2])))
    end
    write_line("INFO", "-----------------")
end

function M.error(msg)
    maybe_rotate()
    write_line("ERROR", msg)
    dfhack.printerr("[Dwarfipelago] ERROR: " .. tostring(msg))
end

-- reqscript returns the script's _ENV; copy exports so callers can use them.
for k, v in pairs(M) do _ENV[k] = v end
return M
