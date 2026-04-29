import { useRef, useState } from 'react';
import { Space, Tag, Select, Button, message, Popconfirm, Drawer, Descriptions, Typography } from 'antd';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { socialLeadService } from '../../services/socialLeadService';
import type { SocialLead, SocialLeadStatus } from '../../types/socialLead';
import StatusTag from '../../components/StatusTag';
import ScoreBar from '../../components/ScoreBar';
import PlatformIcon from '../../components/PlatformIcon';
import ExportButton from '../../components/ExportButton';

const { Paragraph } = Typography;

const statusOptions = [
  { label: '未联系', value: 'uncontacted' },
  { label: '已联系', value: 'contacted' },
  { label: '已回复', value: 'replied' },
  { label: '无效', value: 'invalid' },
];

export default function SocialLeads() {
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [currentLead, setCurrentLead] = useState<SocialLead | null>(null);

  const handleStatusChange = async (id: number, status: SocialLeadStatus) => {
    try {
      await socialLeadService.updateStatus(id, status);
      message.success('状态已更新');
      actionRef.current?.reload();
    } catch {
      message.error('更新失败');
    }
  };

  const handleRowClick = async (record: SocialLead) => {
    try {
      const lead = await socialLeadService.getLead(record.id);
      setCurrentLead(lead);
      setDrawerOpen(true);
    } catch {
      message.error('加载线索详情失败');
    }
  };

  const columns: ProColumns<SocialLead>[] = [
    {
      title: '平台',
      dataIndex: 'platform',
      width: 100,
      valueType: 'select',
      valueEnum: {
        reddit: { text: 'Reddit' },
        bluesky: { text: 'Bluesky' },
        youtube: { text: 'YouTube' },
      },
      render: (_, record) => <PlatformIcon platform={record.platform} />,
    },
    {
      title: '作者',
      dataIndex: 'author_name',
      width: 120,
      render: (_, record) => (
        <a href={record.author_url} target="_blank" rel="noreferrer">
          {record.author_name}
        </a>
      ),
    },
    {
      title: '内容摘要',
      dataIndex: 'content',
      ellipsis: true,
      search: false,
    },
    {
      title: '意向评分',
      dataIndex: 'ai_score',
      width: 150,
      sorter: true,
      render: (_, record) => <ScoreBar score={record.ai_score} />,
    },
    {
      title: '标签',
      dataIndex: 'ai_tags',
      width: 180,
      search: false,
      render: (_, record) => (
        <Space wrap>
          {record.ai_tags?.map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      valueType: 'select',
      valueEnum: {
        uncontacted: { text: '未联系', status: 'Default' },
        contacted: { text: '已联系', status: 'Processing' },
        replied: { text: '已回复', status: 'Success' },
        invalid: { text: '无效', status: 'Error' },
      },
      render: (_, record) => <StatusTag status={record.status} />,
    },
    {
      title: '发布时间',
      dataIndex: 'published_at',
      valueType: 'dateTime',
      width: 180,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {record.post_url && (
            <Button
              type="link"
              size="small"
              href={record.post_url}
              target="_blank"
            >
              查看原帖
            </Button>
          )}
          <Select
            size="small"
            value={record.status}
            style={{ width: 100 }}
            options={statusOptions}
            onChange={(value: SocialLeadStatus) =>
              handleStatusChange(record.id, value)
            }
          />
        </Space>
      ),
    },
  ];

  const handleExport = async (format: 'csv' | 'excel') => {
    return socialLeadService.exportLeads({ format });
  };

  return (
    <>
      <ProTable<SocialLead>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        headerTitle="社媒线索库"
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        tableAlertOptionRender={({ selectedRowKeys: keys }) => (
          <Space size={16}>
            <a onClick={() => setSelectedRowKeys([])}>取消选择</a>
            <ExportButton onExport={handleExport} />
            <span>已选择 {keys.length} 项</span>
          </Space>
        )}
        toolBarRender={() => [
          <ExportButton key="export" onExport={handleExport} />,
        ]}
        request={async (params) => {
          const result = await socialLeadService.getLeads({
            page: params.current || 1,
            page_size: params.pageSize || 20,
            platform: params.platform,
            status: params.status as SocialLeadStatus | undefined,
          });
          return {
            data: result.items,
            total: result.total,
            success: true,
          };
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        scroll={{ x: 1200 }}
        search={{
          labelWidth: 'auto',
          filterType: 'light',
        }}
        onRow={(record) => ({
          onClick: () => handleRowClick(record),
          style: { cursor: 'pointer' },
        })}
      />

      <Drawer
        title="线索详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={600}
      >
        {currentLead && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="平台">
                <PlatformIcon platform={currentLead.platform} />
              </Descriptions.Item>
              <Descriptions.Item label="作者">
                <a href={currentLead.author_url} target="_blank" rel="noreferrer">
                  {currentLead.author_name}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="发布时间">
                {currentLead.published_at}
              </Descriptions.Item>
              <Descriptions.Item label="意向评分">
                <ScoreBar score={currentLead.ai_score} />
              </Descriptions.Item>
              <Descriptions.Item label="标签">
                <Space wrap>
                  {currentLead.ai_tags?.map((tag) => (
                    <Tag key={tag} color="blue">
                      {tag}
                    </Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="来源">
                {currentLead.post_url && (
                  <a href={currentLead.post_url} target="_blank" rel="noreferrer">
                    查看原帖
                  </a>
                )}
              </Descriptions.Item>
            </Descriptions>

            <div>
              <div style={{ marginBottom: 8, fontWeight: 'bold' }}>原始内容：</div>
              <Paragraph ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}>
                {currentLead.content}
              </Paragraph>
            </div>

            {currentLead.ai_analysis && (
              <div>
                <div style={{ marginBottom: 8, fontWeight: 'bold' }}>AI 分析：</div>
                <Paragraph>{currentLead.ai_analysis}</Paragraph>
              </div>
            )}

            <div>
              <div style={{ marginBottom: 8, fontWeight: 'bold' }}>联系状态：</div>
              <Select
                value={currentLead.status}
                style={{ width: 200 }}
                options={statusOptions}
                onChange={async (value: SocialLeadStatus) => {
                  try {
                    await socialLeadService.updateStatus(currentLead.id, value);
                    message.success('状态已更新');
                    setCurrentLead({ ...currentLead, status: value });
                    actionRef.current?.reload();
                  } catch {
                    message.error('更新失败');
                  }
                }}
              />
            </div>
          </Space>
        )}
      </Drawer>
    </>
  );
}
