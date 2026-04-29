import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Spin, message } from 'antd';
import {
  TeamOutlined,
  SearchOutlined,
  UserOutlined,
  ScheduleOutlined,
  ArrowUpOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { dashboardService } from '../../services/dashboardService';
import type { DashboardStats, TrendData } from '../../types/dashboard';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<TrendData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsData, trendsData] = await Promise.all([
        dashboardService.getStats(),
        dashboardService.getTrends({ days: 30 }),
      ]);
      setStats(statsData);
      setTrends(trendsData);
    } catch {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const totalLeads = (stats?.social_leads.total || 0) + (stats?.b2b_leads.total || 0);
  const weekNew = (stats?.social_leads.this_week || 0) + (stats?.b2b_leads.this_week || 0);
  const totalTasks = (stats?.tasks.social_total || 0) + (stats?.tasks.b2b_total || 0);

  const trendOption = {
    title: { text: '线索趋势（近30天）', left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['社媒线索', 'B2B线索'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '16%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trends?.dates || [],
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '社媒线索',
        type: 'line',
        smooth: true,
        data: trends?.social_leads || [],
        itemStyle: { color: '#1677ff' },
        areaStyle: { opacity: 0.15 },
      },
      {
        name: 'B2B线索',
        type: 'line',
        smooth: true,
        data: trends?.b2b_leads || [],
        itemStyle: { color: '#52c41a' },
        areaStyle: { opacity: 0.15 },
      },
    ],
  };

  const platformData = stats?.social_leads.by_platform || {};
  const platformPieOption = {
    title: { text: '平台分布', left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}\n{d}%' },
        data: Object.entries(platformData).map(([name, value]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          value,
        })),
      },
    ],
  };

  const industryData = stats?.b2b_leads.by_industry || {};
  const industryBarOption = {
    title: { text: '行业分布', left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '16%', containLabel: true },
    xAxis: { type: 'category', data: Object.keys(industryData) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: Object.values(industryData),
        itemStyle: {
          color: '#1677ff',
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: '50%',
      },
    ],
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总线索数"
              value={totalLeads}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="社媒线索"
              value={stats?.social_leads.total || 0}
              prefix={<SearchOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="B2B线索"
              value={stats?.b2b_leads.total || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="本周新增"
              value={weekNew}
              prefix={<ArrowUpOutlined />}
              suffix={
                <span style={{ fontSize: 14, color: '#999' }}>
                  / 任务 {totalTasks}
                </span>
              }
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }}>
        <ReactECharts option={trendOption} style={{ height: 350 }} />
      </Card>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={platformPieOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={industryBarOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Card title="任务执行统计" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="总任务"
              value={totalTasks}
              prefix={<ScheduleOutlined />}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="成功率"
              value={(stats?.tasks.success_rate || 0) * 100}
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="社媒任务"
              value={stats?.tasks.social_total || 0}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="B2B任务"
              value={stats?.tasks.b2b_total || 0}
            />
          </Col>
        </Row>
      </Card>

      <Card title="API 额度使用情况" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          {stats?.api_usage &&
            Object.entries(stats.api_usage).map(([name, info]) => (
              <Col xs={24} sm={12} lg={6} key={name}>
                <Card size="small">
                  <Statistic
                    title={name.charAt(0).toUpperCase() + name.slice(1)}
                    value={info.used}
                    suffix={
                      typeof info.limit === 'number'
                        ? `/ ${info.limit}`
                        : `(${info.limit})`
                    }
                  />
                </Card>
              </Col>
            ))}
        </Row>
      </Card>
    </div>
  );
}
