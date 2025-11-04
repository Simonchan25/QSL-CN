import React from 'react'

/**
 * DataTable Component - 通用数据表格组件
 *
 * @param {Array} columns - 列定义数组，每个对象包含:
 *   - title: 列标题
 *   - key: 数据键名
 *   - className: 自定义样式类名 (可选)
 *   - render: 自定义渲染函数 (可选)
 *   - align: 对齐方式 'left' | 'center' | 'right' (可选, 默认'left')
 * @param {Array} data - 数据数组
 * @param {String} className - 表格容器自定义类名 (可选)
 * @param {Boolean} striped - 是否显示斑马纹 (可选, 默认true)
 * @param {Boolean} hoverable - 是否显示hover效果 (可选, 默认true)
 */
const DataTable = ({
  columns = [],
  data = [],
  className = '',
  striped = true,
  hoverable = true
}) => {
  // 如果没有数据或列定义，显示空状态
  if (!columns.length || !data.length) {
    return (
      <div className="data-table-empty" style={{
        textAlign: 'center',
        padding: '2rem',
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: '0.9rem'
      }}>
        {!columns.length ? '未定义表格列' : '暂无数据'}
      </div>
    )
  }

  return (
    <div className={`data-table-wrapper ${className}`}>
      <table className={`data-table ${striped ? 'striped' : ''} ${hoverable ? 'hoverable' : ''}`}>
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th
                key={column.key || index}
                className={column.className || ''}
                style={{ textAlign: column.align || 'left' }}
              >
                {column.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className={striped && rowIndex % 2 === 1 ? 'striped-row' : ''}>
              {columns.map((column, colIndex) => {
                // 获取单元格的值
                const value = row[column.key]

                // 如果有自定义render函数，使用它
                const cellContent = column.render
                  ? column.render(value, row, rowIndex)
                  : value ?? '-'

                return (
                  <td
                    key={`${rowIndex}-${column.key || colIndex}`}
                    className={column.className || ''}
                    style={{ textAlign: column.align || 'left' }}
                  >
                    {cellContent}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default DataTable
