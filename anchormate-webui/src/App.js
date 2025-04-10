import { useState, useEffect } from "react";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Slider,
  IconButton,
  Button,
  Switch,
  FormControlLabel
} from "@mui/material";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import { QRCodeSVG } from "qrcode.react";

const darkTheme = createTheme({ palette: { mode: "dark" } });
// const [autoRunning, setAutoRunning] = useState(false);


function TabPanel({ children, value, index }) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function WindlassControlUI() {
  const [tabIndex, setTabIndex] = useState(0);
  const [depth, setDepth] = useState(0);
  const [targetDepth, setTargetDepth] = useState(10);
  const [armed, setArmed] = useState(false);
  const [autoRunning, setAutoRunning] = useState(false);
  //  const controlUrl = window.location.href;
  const [controlUrl, setControlUrl] = useState(window.location.href);
  const [maxChainLength, setMaxChainLength] = useState(20); // fallback default

  useEffect(() => {
  const fetchInfo = async () => {
    try {
      const res = await fetch("/api/info");
      const data = await res.json();
      setControlUrl(`http://${data.host}:5000`);
      setMaxChainLength(data.chainLength);
    } catch (e) {
      console.error("Failed to fetch host info", e);
    }
  };
  fetchInfo();
}, []);


  useEffect(() => {
    const fetchDepth = async () => {
      try {
        const response = await fetch("/api/depth");
        const data = await response.json();
        setDepth(data.depth);
      } catch (err) {
        console.error("Failed to fetch depth", err);
      }
    };
    fetchDepth();
    const interval = setInterval(fetchDepth, 500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const heartbeat = setInterval(() => {
      fetch("/api/heartbeat", { method: "POST" });
    }, 250);
    return () => clearInterval(heartbeat);
  }, []);

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (armed) {
        e.preventDefault();
        e.returnValue = "Windlass control is armed. Please disarm before leaving.";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [armed]);


  useEffect(() => {
  const checkStatus = async () => {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      setAutoRunning(data.autoRunning);
    } catch (e) {
      console.error("Failed to get status", e);
    }
  };
  checkStatus();
  const interval = setInterval(checkStatus, 500);
  return () => clearInterval(interval);
}, []);  

  const sendManualMove = async (direction) => {
    await fetch("/api/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    });
  };

  const startAutoMove = async () => {
    await fetch("/api/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "START", targetDepth }),
    });
    //setAutoRunning(true);
  };

  const stopAutoMove = async () => {
    await fetch("/api/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "STOP" }),
    });
    //setAutoRunning(false);
  };

  const calibrateDepth = async (depthValue) => {
    await fetch("/api/calibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ depth: depthValue }),
    });
  };

  const toggleArm = async () => {
    if (armed && autoRunning) {
      await stopAutoMove();
    }
    setArmed(!armed);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={{ width: "100vw", height: "100vh", bgcolor: "black", color: "text.primary", overflow: "auto" }}>
        <Box sx={{ p: 2, textAlign: "center" }}>
          <img src="/anchor-logo.png" alt="Anchor Logo" style={{ height: 180 }} />
        </Box>

        <Box display="flex" justifyContent="center" mb={2}>
  	  <FormControlLabel
      control={<Switch checked={armed || autoRunning} onChange={toggleArm} />}
      label="Arm Windlass"
      />
        </Box>

        <Tabs value={tabIndex} onChange={(e, newValue) => setTabIndex(newValue)} centered>
          <Tab label="Manual" />
          <Tab label="Auto" />
          <Tab label="Calibrate" />
        </Tabs>

        <TabPanel value={tabIndex} index={0}>
          <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
            <IconButton color="primary" onMouseDown={() => armed && sendManualMove("UP")} onMouseUp={() => sendManualMove("STOP")} disabled={!armed}>
              <ArrowUpwardIcon fontSize="large" />
            </IconButton>
            <Typography variant="h6">Current Depth: {depth} m</Typography>
            <IconButton color="primary" onMouseDown={() => armed && sendManualMove("DOWN")} onMouseUp={() => sendManualMove("STOP")} disabled={!armed}>
              <ArrowDownwardIcon fontSize="large" />
            </IconButton>
          </Box>
        </TabPanel>

        <TabPanel value={tabIndex} index={1}>
          <Box display="flex" flexDirection="column" alignItems="center" gap={3}>
            <Slider
              value={targetDepth}
              min={0}
              max={maxChainLength}
              step={1}
              onChange={(e, val) => setTargetDepth(val)}
              sx={{ width: "80%" }}
              disabled={!armed}
            />
            <Typography>Target Depth: {targetDepth} m</Typography>
            <Typography variant="h6">Current Depth: {depth} m</Typography>
            <Box display="flex" gap={2}>
              <IconButton color="success" onClick={startAutoMove} disabled={!armed || autoRunning}>
                <PlayArrowIcon fontSize="large" />
              </IconButton>
              <IconButton color="error" onClick={stopAutoMove} disabled={!autoRunning}>
                <StopIcon fontSize="large" />
              </IconButton>
            </Box>
          </Box>
        </TabPanel>

        <TabPanel value={tabIndex} index={2}>
          <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
            <Button variant="contained" onClick={() => calibrateDepth(0)} disabled={!armed}>Anchor is up</Button>
            <Button variant="contained" onClick={() => calibrateDepth(maxChainLength)} disabled={!armed}>Anchor is at chain end</Button>
          </Box>
        </TabPanel>

        <Box display="flex" justifyContent="center" mt={4}>
          <Box textAlign="center">
            <Typography variant="body2">Scan QR to control from phone:</Typography>
            <QRCodeSVG value={controlUrl} size={128} bgColor="#ffffff" fgColor="#000000" />
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
