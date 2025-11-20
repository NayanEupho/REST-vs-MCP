import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt
import numpy as np
import time
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.run_benchmark_advanced import run_all_benchmarks

st.set_page_config(page_title="REST vs MCP Comparison", layout="wide")

st.title("REST vs MCP: The Ultimate Showdown")
st.markdown("""
This dashboard compares **REST API** and **Model Context Protocol (MCP)** across critical metrics for AI Agents.
""")

# Sidebar controls
st.sidebar.header("Benchmark Configuration")
iterations = st.sidebar.slider("Chat Turns", 5, 50, 20)
concurrency = st.sidebar.slider("Concurrent Agents", 10, 100, 50)

new_report = st.sidebar.checkbox("Generate New Report File", value=False, help="Create a timestamped report file instead of overwriting")

if st.sidebar.button("Run Benchmarks"):
    with st.spinner("Running benchmarks... This may take a minute."):
        output_file = "reports/advanced_benchmark_results.csv"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if new_report:
            file_timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"reports/advanced_benchmark_results_{file_timestamp}.csv"
            
        asyncio.run(run_all_benchmarks(output_file, timestamp))
        
        st.success(f"Benchmarks Completed! Saved to {output_file}")
        st.session_state['last_report'] = output_file

# Load results
# Use the last generated report if available, otherwise default
results_path = st.session_state.get('last_report', "reports/advanced_benchmark_results.csv")

if os.path.exists(results_path):
    df = pd.read_csv(results_path)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["Chat Analysis", "Concurrency", "Long Tasks", "Stock Ticker", "Network Resilience", "Tool Chaining", "Real-World Chat", "Report Viewer"])
    
    with tab1:
        st.header("1. Stateful vs Stateless Context")
        st.markdown("Does the protocol remember the conversation?")
        
        chat_data = df[df["scenario"] == "Chat"]
        if not chat_data.empty:
            # Row 1: Charts
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.subheader("Latency Growth")
                
                # Use Altair for interactive chart with trend lines
                
                # Prepare data with trend lines
                trends = []
                for protocol in ["REST", "MCP"]:
                    subset = chat_data[chat_data["protocol"] == protocol].copy()
                    if len(subset) > 1:
                        z = np.polyfit(subset["turn"], subset["latency_ms"], 1)
                        p = np.poly1d(z)
                        subset["trend"] = p(subset["turn"])
                        trends.append(subset)
                
                if trends:
                    final_df = pd.concat(trends)
                    
                    # Base Chart
                    base = alt.Chart(final_df).encode(
                        x=alt.X("turn", title="Chat Turn (Context Size)"),
                        color=alt.Color("protocol", scale=alt.Scale(domain=["REST", "MCP"], range=["#FF4B4B", "#1C83E1"]))
                    )
                    
                    # Scatter Plot (Raw Data)
                    points = base.mark_circle(size=60, opacity=0.6).encode(
                        y=alt.Y("latency_ms", title="Latency (ms)"),
                        tooltip=["protocol", "turn", "latency_ms"]
                    )
                    
                    # Trend Lines
                    lines = base.mark_line().encode(
                        y="trend",
                        strokeDash=alt.condition(
                            alt.datum.protocol == "REST",
                            alt.value([5, 5]),  # Dashed for REST
                            alt.value([0])      # Solid for MCP
                        )
                    )
                    
                    st.altair_chart(points + lines, use_container_width=True)
                st.caption("Dashed/Solid lines represent the linear trend.")
                
            with chart_col2:
                st.subheader("Data Transferred")
                st.line_chart(chat_data, x="turn", y="bytes_sent", color="protocol")

            # Row 2: Verdicts (Aligned)
            verdict_col1, verdict_col2 = st.columns(2)
            
            with verdict_col1:
                st.info("**Verdict (Latency): REST Wins**. In this local simulation, REST's raw HTTP speed outperforms MCP's JSON-RPC/SSE overhead. While REST sends more data, the local network handles it easily. MCP's latency grows faster here due to the overhead of managing stateful sessions in Python implementation.")
                
            with verdict_col2:
                st.info("**Verdict (Bandwidth): MCP Wins (Decisively)**. MCP sends only the new message. REST sends the *entire* conversation history every time, leading to massive bandwidth waste.")

    with tab2:
        st.header("2. High Concurrency (Agent Swarm)")
        st.markdown("How well does it handle 50+ simultaneous agents?")
        
        conc_data = df[df["scenario"] == "Concurrency"]
        if not conc_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Latency Distribution")
                fig, ax = plt.subplots(figsize=(10, 4))
                sns.boxplot(data=conc_data, x="protocol", y="latency_ms", ax=ax)
                st.pyplot(fig)
            
            with col2:
                st.subheader("Data Transfer (Bytes Sent)")
                # Bar chart for average bytes sent
                avg_bytes = conc_data.groupby("protocol")["bytes_sent"].mean().reset_index()
                st.bar_chart(avg_bytes, x="protocol", y="bytes_sent")

            avg_rest = conc_data[conc_data["protocol"] == "REST"]["latency_ms"].mean()
            avg_mcp = conc_data[conc_data["protocol"] == "MCP"]["latency_ms"].mean()
            
            st.metric("REST Avg Latency", f"{avg_rest:.2f} ms")
            st.metric("MCP Avg Latency", f"{avg_mcp:.2f} ms")
            
            st.info("**Winner: Tie/Context Dependent**. Both use HTTP under the hood. However, MCP's persistent connection *can* be more efficient if keep-alive is optimized, but standard HTTP/2 also handles this well.")

    with tab3:
        st.header("3. Long Running Tasks (Push vs Pull)")
        st.markdown("Waiting for a slow tool (e.g., Code Generation).")
        
        task_data = df[df["scenario"] == "Long Task"]
        if not task_data.empty:
            st.dataframe(task_data)
            
            col1, col2 = st.columns(2)
            with col1:
                 st.metric("REST Overhead (Polls)", int(task_data[task_data["protocol"]=="REST"]["overhead_requests"].iloc[0]))
            with col2:
                 st.metric("MCP Overhead (Events)", int(task_data[task_data["protocol"]=="MCP"]["overhead_requests"].iloc[0]))

            st.info("**Winner: MCP**. REST requires polling (wasted requests). MCP pushes progress events via SSE.")

    with tab4:
        st.header("4. Real-time Stock Ticker")
        st.markdown("Simulating a live market feed.")
        
        stock_data = df[df["scenario"] == "Stock Ticker"]
        if not stock_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("MCP Requests (5s)", int(stock_data[stock_data["protocol"]=="MCP"]["overhead_requests"].iloc[0]))
            with col2:
                st.metric("REST Requests (5s)", int(stock_data[stock_data["protocol"]=="REST"]["overhead_requests"].iloc[0]))
                
            st.bar_chart(stock_data, x="protocol", y="overhead_requests")
            
            st.info("**Winner: MCP**. Subscriptions eliminate the need for constant polling, reducing network traffic while keeping data fresh.")

    with tab5:
        st.header("5. Network Resilience")
        st.markdown("Simulating poor network conditions (Latency + Packet Loss).")
        
        net_data = df[df["scenario"] == "Network Instability"]
        if not net_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("MCP Success Rate", f"{net_data[net_data['protocol']=='MCP']['success_rate'].iloc[0]}%")
            with col2:
                st.metric("REST Success Rate", f"{net_data[net_data['protocol']=='REST']['success_rate'].iloc[0]}%")
                
            st.bar_chart(net_data, x="protocol", y="success_rate")
            
            st.warning("Note: High packet loss affects both, but stateful connections (MCP) may require more complex reconnection logic.")

    with tab6:
        st.header("6. Tool Chaining")
        st.markdown("Simulating a 3-step sequential workflow (Ingest -> Analyze -> Summarize).")
        
        chain_data = df[df["scenario"] == "Tool Chaining"]
        if not chain_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("MCP Latency", f"{chain_data[chain_data['protocol']=='MCP']['latency_ms'].iloc[0]:.2f} ms")
            with col2:
                st.metric("REST Latency", f"{chain_data[chain_data['protocol']=='REST']['latency_ms'].iloc[0]:.2f} ms")
                
            st.bar_chart(chain_data, x="protocol", y="latency_ms")
            
            st.info("REST is often faster for simple sequential chains due to lower parsing overhead. MCP's strength lies in complex, dynamic agentic workflows where the server decides the next step.")

    with tab7:
        st.header("7. Real-World Chat Simulation")
        st.markdown("Simulating 4G Network Conditions (50ms Latency, 5 Mbps Bandwidth).")
        
        rw_data = df[df["scenario"] == "Real-World Chat"]
        if not rw_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Latency Impact")
                st.line_chart(rw_data, x="turn", y="latency_ms", color="protocol")
            with col2:
                st.subheader("Data Transfer")
                st.line_chart(rw_data, x="turn", y="bytes_sent", color="protocol")
                
            st.success("**Verdict: MCP Wins**. Under real-world constraints, REST's bandwidth usage causes massive latency spikes. MCP remains efficient.")

    with tab8:
        st.header("Generated Report")
        md_path = results_path.replace(".csv", ".md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            st.markdown(report_content)
        else:
            st.warning("No Markdown report found for this run.")

else:
    st.warning("No benchmark results found. Click 'Run Benchmarks' in the sidebar.")
