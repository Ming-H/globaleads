import { useRef, useState } from 'react';
import { Space, Tag, Select, Button, message, Drawer, Descriptions } from 'antd';
import {
  CopyOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { b2bLeadService } from '../../services/b2bLeadService';
import type { B2BLead, B2BLeadStatus } from '../../types/b2bLead';
import StatusTag from '../../components/StatusTag';
import PlatformIcon from '../../components/PlatformIcon';
import ExportButton from '../../components/ExportButton';

const statusOptions = [
  { label: '未联系', value: 'uncontacted' },
  { label: '已联系', value: 'contacted' },
  { label: '已回复', value: 'replied' },
  { label: '无效', value: 'invalid' },
];

export default function B2BLeads() {
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [currentLead, setCurrentLead] = useState<B2BLead | null>(null);

  const handleStatusChange = async (id: number, status: B2BLeadStatus) => {
    try {
      await b2bLeadService.updateStatus(id, status);
      message.success('状态已更新');
      actionRef.current?.reload();
    } catch {
      message.error('更新失败');
    }
  };

  const handleRowClick = async (record: B2BLead) => {
    try {
      const lead = await b2bLeadService.getLead(record.id);
      setCurrentLead(lead);
      setDrawerOpen(true);
    } catch {
      message.error('加载线索详情失败');
    }
  };

  const columns: ProColumns<B2BLead>[] = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      width: 200,
      render: (_, record) =>
        record.company_website ? (
          <a href={record.company_website} target="_blank" rel="noreferrer">
            {record.company_name}
          </a>
        ) : (
          record.company_name
        ),
    },
    {
      title: '联系人',
      dataIndex: 'contact_name',
      width: 120,
      search: false,
    },
    {
      title: '邮箱',
      dataIndex: 'contact_email',
      width: 200,
      search: false,
      render: (_, record) =>
        record.contact_email ? (
          <a href={`mailto:${record.contact_email}`}>{record.contact_email}</a>
        ) : (
          <Tag>无邮箱</Tag>
        ),
    },
    {
      title: '行业',
      dataIndex: 'industry',
      width: 120,
      valueType: 'select',
      valueEnum: {
        Lighting: { text: 'Lighting' },
        Electronics: { text: 'Electronics' },
        Manufacturing: { text: 'Manufacturing' },
      },
    },
    {
      title: '地区',
      dataIndex: 'region',
      width: 140,
      valueType: 'select',
      valueEnum: {
        'United States': { text: '美国' },
        'United Kingdom': { text: '英国' },
        Germany: { text: '德国' },
      },
    },
    {
      title: '数据源',
      dataIndex: 'data_source',
      width: 120,
      valueType: 'select',
      valueEnum: {
        google_search: { text: 'Google Search' },
        osm: { text: 'OpenStreetMap' },
      },
      render: (_, record) => <PlatformIcon platform={record.data_source} />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
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
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {record.company_website && (
            <Button
              type="link"
              size="small"
              href={record.company_website}
              target="_blank"
            >
              访问网站
            </Button>
          )}
          <Select
            size="small"
            value={record.status}
            style={{ width: 100 }}
            options={statusOptions}
            onChange={(value: B2BLeadStatus) =>
              handleStatusChange(record.id, value)
            }
          />
        </Space>
      ),
    },
  ];

  const handleExport = async (format: 'csv' | 'excel') => {
    return b2bLeadService.exportLeads({ format });
  };

  return (
    <>
      <ProTable<B2BLead>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        headerTitle="B2B线索库"
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
          const result = await b2bLeadService.getLeads({
            page: params.current || 1,
            page_size: params.pageSize || 20,
            industry: params.industry,
            region: params.region,
            data_source: params.data_source,
            status: params.status as B2BLeadStatus | undefined,
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
        scroll={{ x: 1300 }}
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
              <Descriptions.Item label="公司名称">
                {currentLead.company_website ? (
                  <a href={currentLead.company_website} target="_blank" rel="noreferrer">
                    {currentLead.company_name}
                  </a>
                ) : (
                  currentLead.company_name
                )}
              </Descriptions.Item>
              <Descriptions.Item label="公司网站">
                {currentLead.company_website ? (
                  <a href={currentLead.company_website} target="_blank" rel="noreferrer">
                    {currentLead.company_website}
                  </a>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="公司规模">
                {currentLead.company_size || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="公司地址">
                {currentLead.company_address || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="行业">
                {currentLead.industry}
              </Descriptions.Item>
              <Descriptions.Item label="地区">
                {currentLead.region}
              </Descriptions.Item>
              <Descriptions.Item label="联系人">
                {currentLead.contact_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="联系人职位">
                {currentLead.contact_title || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="联系邮箱">
                {currentLead.contact_email ? (
                  <Space>
                    <a href={`mailto:${currentLead.contact_email}`}>{currentLead.contact_email}</a>
                    <Button
                      type="link"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => {
                        navigator.clipboard.writeText(currentLead.contact_email);
                        message.success('已复制邮箱');
                      }}
                    />
                  </Space>
                ) : (
                  '无邮箱'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="联系电话">
                {currentLead.contact_phone ? (
                  <Space>
                    <span>{currentLead.contact_phone}</span>
                    <Button
                      type="link"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => {
                        navigator.clipboard.writeText(currentLead.contact_phone!);
                        message.success('已复制电话');
                      }}
                    />
                  </Space>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Twitter/X">
                {currentLead.contact_twitter ? (
                  <a href={`https://x.com/${currentLead.contact_twitter}`} target="_blank" rel="noreferrer">
                    @{currentLead.contact_twitter}
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="LinkedIn">
                {currentLead.contact_linkedin ? (
                  <a href={currentLead.contact_linkedin} target="_blank" rel="noreferrer">
                    查看LinkedIn
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Facebook">
                {currentLead.contact_facebook ? (
                  <a href={currentLead.contact_facebook} target="_blank" rel="noreferrer">
                    查看Facebook
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="数据源">
                <PlatformIcon platform={currentLead.data_source} />
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <StatusTag status={currentLead.status} />
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {currentLead.created_at}
              </Descriptions.Item>
            </Descriptions>

            <div>
              <div style={{ marginBottom: 8, fontWeight: 'bold' }}>联系状态：</div>
              <Select
                value={currentLead.status}
                style={{ width: 200 }}
                options={statusOptions}
                onChange={async (value: B2BLeadStatus) => {
                  try {
                    await b2bLeadService.updateStatus(currentLead.id, value);
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
